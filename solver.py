import pandas as pd
import cpmpy as cp
import streamlit

def get_player(row)-> dict:
    return {
        "name": row.Name,
        "rank": row.Rank,
        "positions": set([pos[0].upper() for pos in [row.Position_1, row.Position_2] if (pos and str(pos) and str(pos) != "nan")])
    }

def get_players(file:streamlit.runtime.uploaded_file_manager.UploadedFile) -> list[dict]:
    df = pd.read_excel(file)
    df = df.rename(columns=lambda x: x.replace(' ', '_'))
    return [get_player(row) for row in df.itertuples()]

def get_rank_dict(players:list[dict]) -> dict[float, int]:
    rank_dict = {}
    for player in players:
        rank = player["rank"]
        if rank not in rank_dict:
            rank_dict[rank] = 0
        rank_dict[rank] += 1
    return rank_dict

def solve(file: streamlit.runtime.uploaded_file_manager.UploadedFile, 
          n_teams:int, 
          min_forwards_per_team: int, 
          min_defenders_per_team:int,
          per_rank_tier_balance_weight: int,
          rank_sum_balance_weight: int,
          forwards_balance_weight,
          defenders_balance_weight) -> list[str]:

    # Fixed weights
    team_size_balance_weight = 10
    min_forwards_met_weight = 20
    min_defenders_met_weight = 20

    # Parse excel file
    players = get_players(file)
    n_players = len(players)
    rank_dict = get_rank_dict(players)

    # Solve the problem
    """
    ATTRIBUTIONS
    - https://cpmpy.readthedocs.io/en/latest/modeling.html
    - Used Claude AI to translate desired rules into cpmpy constraints for the assignment/minimization problem
    (Reviewed generated code to verify correctness)
    """
    # x = assignment table (n_players, n_teams)
    x = cp.boolvar(shape=(n_players, n_teams), name="x")  # x[p,t] = 1 if player p on team t

    # Initialize the model
    model = cp.Model()

    # HARD CONSTRAINT: each player on exactly one team
    model += (x.sum(axis=1) == 1)

    # HARD: flex player can only be a forward OR a defender in a game
    is_flex = [p["positions"] == set(["F", "D"]) for p in players]
    y = cp.boolvar(shape=n_players, name="is_forward")  # y = tracks if player is assigned as a forward (1 = counts as F)
    for p in range(n_players):
        if not is_flex[p]:
            model += (y[p] == (1 if "F" in players[p]["positions"] else 0))

    # Track soft constraint penalties
    penalties = []

    # SOFT: teams are evenly sized (only differ by at most 1 player)
    team_sizes = x.sum(axis=0)
    size_diff = cp.max(team_sizes) - cp.min(team_sizes)
    penalties.append(team_size_balance_weight * size_diff)

    # SOFT: forward/defender minimums met
    for t in range(n_teams):
        forwards_on_team = cp.sum(y[p] * x[p, t] for p in range(n_players))
        defenders_on_team = cp.sum((1 - y[p]) * x[p, t] for p in range(n_players))
        penalties.append(min_forwards_met_weight * cp.max([min_forwards_per_team - forwards_on_team, 0]))
        penalties.append(min_defenders_met_weight * cp.max([min_defenders_per_team - defenders_on_team, 0]))

    # SOFT: similar number of forwards per team
    forwards_per_team = [cp.sum(y[p] * x[p, t] for p in range(n_players)) for t in range(n_teams)]
    forward_diff = cp.max(forwards_per_team) - cp.min(forwards_per_team)
    penalties.append(forwards_balance_weight * forward_diff)

    # SOFT: similar number of defenders per team
    defenders_per_team = [cp.sum((1 - y[p]) * x[p, t] for p in range(n_players)) for t in range(n_teams)]
    defender_diff = cp.max(defenders_per_team) - cp.min(defenders_per_team)
    penalties.append(defenders_balance_weight * defender_diff)

    # SOFT: per-rank-tier loop (avoid having a team be all 1's and 6's and another all 3-4's)
    rank_values = sorted(rank_dict.keys())
    for rank in rank_values:
        # indices of players at this rank
        idxs = [p for p in range(n_players) if players[p]["rank"] == rank]
        # how many players at this rank end up on each team
        counts_per_team = [cp.sum(x[p, t] for p in idxs) for t in range(n_teams)]
        # diff in counts of players per rank between teams
        tier_diff = cp.max(counts_per_team) - cp.min(counts_per_team)
        # penalty for imbalanced player rank distribution
        penalties.append(per_rank_tier_balance_weight * tier_diff)

    # SOFT: overall rank-sum balance
    ranks = [int(p["rank"] * 2) for p in players]   # 1.0 -> 2, 1.5 -> 3, etc. (scaled to ints to be compatible with Google OR-tools CP-SAT)
    team_rank_totals = [cp.sum(ranks[p] * x[p, t] for p in range(n_players)) for t in range(n_teams)]
    rank_diff = cp.abs(team_rank_totals[0] - team_rank_totals[1])
    penalties.append(rank_sum_balance_weight * rank_diff)

    # Minimize sum of penalties
    model.minimize(cp.sum(penalties))

    lines = []
    if model.solve():
        for t in range(n_teams):
            lines.append(f"Team {t+1}:")
            team = { "F": {}, "D": {} }
            for p in range(n_players):
                if x[p, t].value():
                    role = "F" if y[p].value() else "D"
                    flex_tag = " (flex)" if is_flex[p] else ""
                    player_rank = players[p]['rank']
                    if player_rank not in team[role]:
                        team[role][player_rank] = []
                    team[role][player_rank].append({"name": players[p]["name"], "role": f"{role}{flex_tag}"})
            for pos in team.keys():
                rank_values = sorted(team[pos].keys())
                i = 1
                for rank in rank_values:
                    for p in team[pos][rank]:
                        lines.append(f"  {i}. {p['role']} - {p['name']} ({rank})")
                        i = i + 1
                lines.append("")
            lines.append("")
    else:
        lines.append("Even the relaxed model is infeasible — check that x.sum(axis=1)==1 is satisfiable at all")

    return lines
