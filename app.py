import streamlit as st
import solver

st.title("Hockey Team Planner :ice_hockey:")

TEMPLATE_FILEPATH = "players.xlsx"

with open(TEMPLATE_FILEPATH, "rb") as template_file:
    st.download_button(
        label="Download Template",
        data=template_file,
        file_name=TEMPLATE_FILEPATH,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with st.form("form", clear_on_submit=False, enter_to_submit=False):

    uploaded_file = st.file_uploader("Import player spreadsheet (download the template above for an example)", type=["xlsx"])

    n_teams = st.number_input("Number of teams", min_value=2, max_value=10, step=1)
    min_forwards_per_team = st.number_input("Minimum forwards per team", min_value=3, max_value=10, step=1)
    min_defenders_per_team = st.number_input("Minimum defenders per team", min_value=2, max_value=6, step=1)

    st.markdown("**Adjust importance of soft constraints. Higher value means more important.**")

    per_rank_tier_balance_weight = st.slider(
        label="Even distribution of players by rank per team (prevents team of all 1's and 6's vs team of 3-5's)", 
        min_value=0, max_value=30, value=20, step=5)

    rank_sum_balance_weight = st.slider(
        label="Sum of player rankings per team are similar", 
        min_value=0, max_value=30, value=5, step=5)

    forwards_balance_weight = st.slider(
        label="Similar number of forwards per team", 
        min_value=0, max_value=30, value=10, step=5)

    defenders_balance_weight = st.slider(
        label="Similar number of defenders per team", 
        min_value=0, max_value=30, value=15, step=5)


    test = st.form_submit_button("Try with Template File", type="secondary")
    if test:
        result = solver.solve(
            file=TEMPLATE_FILEPATH,
            n_teams=n_teams,
            min_forwards_per_team=min_forwards_per_team,
            min_defenders_per_team=min_defenders_per_team,
            per_rank_tier_balance_weight=per_rank_tier_balance_weight,
            rank_sum_balance_weight=rank_sum_balance_weight,
            forwards_balance_weight=forwards_balance_weight,
            defenders_balance_weight=defenders_balance_weight
        )
        st.markdown("**Generated Teams:**")
        for line in result:
            st.write(line)

    submitted = st.form_submit_button("Submit", type="primary")
    if submitted:
        if uploaded_file is None:
            st.warning("Please upload a file before submitting")
        else:
            result = solver.solve(
                file=uploaded_file,
                n_teams=n_teams,
                min_forwards_per_team=min_forwards_per_team,
                min_defenders_per_team=min_defenders_per_team,
                per_rank_tier_balance_weight=per_rank_tier_balance_weight,
                rank_sum_balance_weight=rank_sum_balance_weight,
                forwards_balance_weight=forwards_balance_weight,
                defenders_balance_weight=defenders_balance_weight
            )
            st.markdown("**Generated Teams:**")
            for line in result:
                st.write(line)



