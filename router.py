def route_from_scores(scores: dict): 
    selected = [d for d, s in scores.items() if s > 0.35]
    if not selected:
        sorted_depts = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        selected = [sorted_depts[0][0]]
        if len(sorted_depts) > 1 and sorted_depts[1][1] > 0.1:
            selected.append(sorted_depts[1][0])

    max_score = max([scores[d] for d in selected]) if selected else 0.0
    if max_score > 0.7:
        priority = 'high'
    elif max_score > 0.4:
        priority = 'medium'
    else:
        priority = 'low'

    return {"departments": selected, "priority": priority, "scores": scores}
