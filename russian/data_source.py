

async def rank(player_data: dict, group_id: int, itype) -> str:
    group_id = str(group_id)
    all_user = list(player_data[group_id].keys())
    if itype == 'gold_rank':
        rank_name = '\t金币排行榜\n'
        all_user_data = [player_data[group_id][x]['gold'] for x in all_user]
    elif itype == 'win_rank':
        rank_name = '\t胜场排行榜\n'
        all_user_data = [player_data[group_id][x]['win_count'] for x in all_user]
    elif itype == 'lose_rank':
        rank_name = '\t败场排行榜\n'
        all_user_data = [player_data[group_id][x]['lose_count'] for x in all_user]
    elif itype == 'make_gold':
        rank_name = '\t赢取金币排行榜\n'
        all_user_data = [player_data[group_id][x]['make_gold'] for x in all_user]
    else:
        rank_name = '\t输掉金币排行榜\n'
        all_user_data = [player_data[group_id][x]['lose_gold'] for x in all_user]
    rst = ''
    if all_user:
        for _ in range(len(all_user) if len(all_user) < 10 else 10):
            _max = max(all_user_data)
            _max_id = all_user[all_user_data.index(_max)]
            name = player_data[group_id][_max_id]['nickname']
            rst += f'{name}：{_max}\n'
            all_user_data.remove(_max)
            all_user.remove(_max_id)
        rst = rst[:-1]
    return rank_name + rst


def end_handle(player_data: dict, win_user_id: int, lose_user_id, group_id: int, gold: int, fee: int):
    win_user_id = str(win_user_id)
    lose_user_id = str(lose_user_id)
    group_id = str(group_id)
    player_data[group_id][win_user_id]['gold'] += gold - fee
    player_data[group_id][win_user_id]['make_gold'] += gold - fee
    player_data[group_id][win_user_id]['win_count'] += 1

    player_data[group_id][lose_user_id]['gold'] -= gold
    player_data[group_id][lose_user_id]['lose_gold'] += gold
    player_data[group_id][lose_user_id]['lose_count'] += 1

    return player_data


