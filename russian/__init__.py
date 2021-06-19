from nonebot import on_command, require
import random
import asyncio
from nonebot.adapters.cqhttp import GROUP, Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.typing import T_State
from .util import get_message_text, is_number, get_message_at
import time
from .data_source import rank, end_handle
from pathlib import Path
import os
import nonebot
try:
    import ujson as json
except ModuleNotFoundError:
    import json

__plugin_name__ = '俄罗斯轮盘'

__plugin_usage__ = '''俄罗斯轮盘帮助：
    开启游戏：装弹 [子弹数] [金额](默认200金币) [at](指定决斗对象，为空则所有群友都可接受决斗)
        示例：装弹 1 10
    接受对决：接受对决/拒绝决斗
    开始对决：开枪（轮流开枪，30秒未开枪另一方可使用‘结算’命令结束对决并胜利）
    结算：结算（当某一方30秒未开枪，可使用该命令强行结束对决并胜利）
    我的战绩：我的战绩
    排行榜：胜场排行/败场排行/欧洲人排行/慈善家排行
    【注：同一时间群内只能有一场对决】
'''

scheduler = require("nonebot_plugin_apscheduler").scheduler

driver: nonebot.Driver = nonebot.get_driver()

sign_gold = driver.config.sign_gold if driver.config.sign_gold else [1, 100]
max_bet_gold = driver.config.max_bet_gold if driver.config.max_bet_gold else 1000
russian_path = driver.config.russian_path if driver.config.russian_path else ''

player_data = {}
if russian_path:
    file = Path(russian_path) / 'russian_data.json'
    file.parent.mkdir(exist_ok=True, parents=True)
    if file.exists():
        player_data = json.load(open(file, 'r', encoding='utf8'))
    else:
        old_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'russian_data.json'))
        if os.path.exists(old_file):
            os.rename(old_file, file)
            player_data = json.load(open(file, 'r', encoding='utf8'))

else:
    file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'russian_data.json'))
    if os.path.exists(file):
        player_data = json.load(open(file, 'r', encoding='utf8'))


rs_player = {}

sign = on_command('轮盘签到', permission=GROUP, priority=5, block=True)

rssian = on_command('俄罗斯轮盘', aliases={'装弹', '俄罗斯转盘'}, permission=GROUP, priority=5, block=True)

accept = on_command('接受对决', aliases={'接受决斗', '接受挑战'}, permission=GROUP, priority=5, block=True)

refuse = on_command('拒绝对决', aliases={'拒绝决斗', '拒绝挑战'}, permission=GROUP, priority=5, block=True)

shot = on_command('开枪', aliases={'咔', '嘭', '嘣'}, permission=GROUP, priority=5, block=True)

settlement = on_command('结算', permission=GROUP, priority=5, block=True)

record = on_command('我的战绩', permission=GROUP, priority=5, block=True)

rssian_rank = on_command('胜场排行', aliases={'金币排行', '胜利排行', '败场排行', '失败排行',
                                          '欧洲人排行', '慈善家排行'}, permission=GROUP, priority=5, block=True)

my_gold = on_command('我的金币', permission=GROUP, priority=5, block=True)


@sign.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    global player_data
    player_is_exists(event)
    if player_data[str(event.group_id)][str(event.user_id)]['is_sign']:
        await sign.finish('贪心的人是不会有好运的...', at_sender=True)
    gold = random.randint(sign_gold[0], sign_gold[1])
    player_data[str(event.group_id)][str(event.user_id)]['gold'] += gold
    player_data[str(event.group_id)][str(event.user_id)]['make_gold'] += gold
    player_data[str(event.group_id)][str(event.user_id)]['is_sign'] = True
    await sign.send(random.choice([f'这是今天的钱，祝你好运...', '今天可别输光光了.']) + f'\n你获得了 {gold} 金币', at_sender=True)
    with open(file, 'w', encoding='utf8') as f:
        json.dump(player_data, f, ensure_ascii=False, indent=4)


@accept.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    global rs_player, player_data
    player_is_exists(event)
    try:
        if rs_player[event.group_id][1] == 0:
            await accept.finish('目前没有发起对决，你接受个啥？速速装弹！', at_sender=True)
    except KeyError:
        await accept.finish('目前没有进行的决斗，请发送 装弹 开启决斗吧！', at_sender=True)
    if rs_player[event.group_id][2] != 0:
        if rs_player[event.group_id][1] == event.user_id or rs_player[event.group_id][2] == event.user_id:
            await accept.finish(f'你已经身处决斗之中了啊，给我认真一点啊！', at_sender=True)
        else:
            await accept.finish('已经有人接受对决了，你还是乖乖等待下一场吧！', at_sender=True)
    if rs_player[event.group_id][1] == event.user_id:
        await accept.finish('请不要自己枪毙自己！换人来接受对决...', at_sender=True)
    if rs_player[event.group_id]['at'] != 0 and rs_player[event.group_id]['at'] != event.user_id:
        await accept.finish(Message(f'这场对决是邀请 {MessageSegment.at(rs_player[event.group_id]["at"])}的，不要捣乱！'),
                            at_sender=True)
    if time.time() - rs_player[event.group_id]['time'] > 30:
        rs_player[event.group_id] = {}
        await accept.finish('这场对决邀请已经过时了，请重新发起决斗...', at_sender=True)

    user_money = player_data[str(event.group_id)][str(event.user_id)]['gold']
    if user_money < rs_player[event.group_id]['money']:
        if rs_player[event.group_id]['at'] != 0 and rs_player[event.group_id]['at'] == event.user_id:
            rs_player[event.group_id] = {}
            await accept.finish('你的金币不足以接受这场对决！对决还未开始便结束了，请重新装弹！', at_sender=True)
        else:
            await accept.finish('你的金币不足以接受这场对决！', at_sender=True)

    player2_name = event.sender.card if event.sender.card else event.sender.nickname

    rs_player[event.group_id][2] = event.user_id
    rs_player[event.group_id]['player2'] = player2_name
    rs_player[event.group_id]['time'] = time.time()

    await accept.send(Message(f'{player2_name}接受了对决！\n'
                              f'请{MessageSegment.at(rs_player[event.group_id][1])}先开枪！'))


@refuse.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    global rs_player
    player_is_exists(event)
    try:
        if rs_player[event.group_id][1] == 0:
            await accept.finish('你要拒绝啥？明明都没有人发起对决的说！', at_sender=True)
    except KeyError:
        await refuse.finish('目前没有进行的决斗，请发送 装弹 开启决斗吧！', at_sender=True)
    if rs_player[event.group_id]['at'] != 0 and event.user_id != rs_player[event.group_id]['at']:
        await accept.finish('又不是找你决斗，你拒绝什么啊！气！', at_sender=True)
    if rs_player[event.group_id]['at'] == event.user_id:
        at_player_name = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
        at_player_name = at_player_name['card'] if at_player_name['card'] else at_player_name['nickname']
        await accept.send(Message(f'{MessageSegment.at(rs_player[event.group_id][1])}\n'
                                  f'{at_player_name}拒绝了你的对决！'))
        rs_player[event.group_id] = {}


@settlement.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    global rs_player
    player_is_exists(event)
    if not rs_player.get(event.group_id) or rs_player[event.group_id][1] == 0 or rs_player[event.group_id][2] == 0:
        await settlement.finish('比赛并没有开始...无法结算...', at_sender=True)
    if event.user_id != rs_player[event.group_id][1] and event.user_id != rs_player[event.group_id][2]:
        await settlement.finish('吃瓜群众不要捣乱！黄牌警告！', at_sender=True)
    if time.time() - rs_player[event.group_id]['time'] <= 30:
        await settlement.finish(f'{rs_player[event.group_id]["player1"]} 和'
                                f' {rs_player[event.group_id]["player2"]} 比赛并未超时，请继续比赛...')
    win_name = rs_player[event.group_id]["player1"] if \
        rs_player[event.group_id][2] == rs_player[event.group_id]['next'] else \
        rs_player[event.group_id]["player2"]
    await settlement.send(f'这场对决是 {win_name} 胜利了')
    await end_game(bot, event)


@rssian.args_parser
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    player_is_exists(event)
    msg = get_message_text(event.json())
    if msg in ['取消', '算了']:
        await rssian.finish('已取消操作...')
    try:
        if rs_player[event.group_id][1] != 0:
            await rssian.finish('决斗已开始...', at_sender=True)
    except KeyError:
        pass
    if not is_number(msg):
        await rssian.reject('输入子弹数量必须是数字啊喂！')
    if int(msg) < 1 or int(msg) > 6:
        await rssian.reject('子弹数量必须大于0小于7！')
    state['bullet_num'] = int(msg)


@rssian.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    global rs_player
    player_is_exists(event)
    msg = get_message_text(event.json())
    if msg == '帮助':
        await rssian.finish(__plugin_usage__)
    try:
        if rs_player[event.group_id][1] and not rs_player[event.group_id][2] and \
                time.time() - rs_player[event.group_id]['time'] <= 30:
            await rssian.finish(f'现在是 {rs_player[event.group_id]["player1"]} 发起的对决\n请等待比赛结束后再开始下一轮...')
        if rs_player[event.group_id][1] and rs_player[event.group_id][2] and \
                time.time() - rs_player[event.group_id]['time'] <= 30:
            await rssian.finish(f'{rs_player[event.group_id]["player1"]} 和'
                                f' {rs_player[event.group_id]["player2"]}的对决还未结束！')
        if rs_player[event.group_id][1] and rs_player[event.group_id][2] and \
                time.time() - rs_player[event.group_id]['time'] > 30:
            await shot.send('决斗已过时，强行结算...')
            await end_game(bot, event)
            return
        if not rs_player[event.group_id][2] and time.time() - rs_player[event.group_id]['time'] > 30:
            rs_player[event.group_id][1] = 0
            rs_player[event.group_id][2] = 0
            rs_player[event.group_id]['at'] = 0
    except KeyError:
        pass
    if msg:
        msg = msg.split(' ')
        if len(msg) == 1:
            msg = msg[0]
            if is_number(msg) and not (int(msg) < 1 or int(msg) > 6):
                state['bullet_num'] = int(msg)
        else:
            money = msg[1].strip()
            msg = msg[0].strip()
            if is_number(msg) and not (int(msg) < 1 or int(msg) > 6):
                state['bullet_num'] = int(msg)
            if is_number(money) and 0 < int(money) <= max_bet_gold:
                state['money'] = int(money)
    state['at'] = get_message_at(event.json())


@rssian.got("bullet_num", prompt='请输入装填子弹的数量！(最多6颗)')
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    global rs_player, player_data
    player_is_exists(event)
    bullet_num = state['bullet_num']
    at_ = state['at']
    money = state['money'] if state.get('money') else 200
    user_money = player_data[str(event.group_id)][str(event.user_id)]['gold']
    if bullet_num < 0 or bullet_num > 6:
        await rssian.reject('子弹数量必须大于0小于7！速速重新装弹！')
    if money > max_bet_gold:
        await rssian.finish(f'太多了！单次金额不能超过{max_bet_gold}！', at_sender=True)
    if money > user_money:
        await rssian.finish('你没有足够的钱支撑起这场挑战', at_sender=True)

    player1_name = event.sender.card if event.sender.nickname else event.sender.nickname

    if at_:
        at_ = at_[0]
        at_player_name = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
        at_player_name = at_player_name['card'] if at_player_name['card'] else at_player_name['nickname']
        msg = f'{player1_name} 向 {MessageSegment.at(at_)} 发起了决斗！请 {at_player_name} 在30秒内回复‘接受对决’ or ‘拒绝对决’，超时此次决斗作废！'
    else:
        at_ = 0
        msg = '若30秒内无人接受挑战则此次对决作废【首次游玩请发送 ’俄罗斯轮盘帮助‘ 来查看命令】'

    rs_player[event.group_id] = {1: event.user_id,
                                 'player1': player1_name,
                                 2: 0,
                                 'player2': '',
                                 'at': at_,
                                 'next': event.user_id,
                                 'money': money,
                                 'bullet': random_bullet(bullet_num),
                                 'bullet_num': bullet_num,
                                 'null_bullet_num': 7 - bullet_num,
                                 'index': 0,
                                 'time': time.time()}

    await rssian.send(Message(('咔 ' * bullet_num)[:-1] + f'，装填完毕\n挑战金额：{money}\n'
                                                         f'第一枪的概率为：{str(float(bullet_num) / 7.0 * 100)[:5]}%\n'
                                                         f'{msg}'))


@shot.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    global rs_player
    player_is_exists(event)
    try:
        if time.time() - rs_player[event.group_id]['time'] > 30:
            if rs_player[event.group_id][2] == 0:
                rs_player[event.group_id][1] = 0
                await shot.finish('这场对决已经过时了，请重新装弹吧！', at_sender=True)
            else:
                await shot.send('决斗已过时，强行结算...')
                await end_game(bot, event)
                return
    except KeyError:
        await shot.finish('目前没有进行的决斗，请发送 装弹 开启决斗吧！', at_sender=True)
    if rs_player[event.group_id][1] == 0:
        await shot.finish('没有对决，也还没装弹呢，请先输入 装弹 吧！', at_sender=True)
    if rs_player[event.group_id][1] == event.user_id and rs_player[event.group_id][2] == 0:
        await shot.finish('baka，你是要枪毙自己嘛笨蛋！', at_sender=True)
    if rs_player[event.group_id][2] == 0:
        await shot.finish('请这位勇士先发送 接受对决 来站上擂台...', at_sender=True)
    player1_name = rs_player[event.group_id]['player1']
    player2_name = rs_player[event.group_id]['player2']
    if rs_player[event.group_id]['next'] != event.user_id:
        if event.user_id != rs_player[event.group_id][1] and event.user_id != rs_player[event.group_id][2]:
            nickname = event.sender.card if event.sender.card else event.sender.nickname
            await shot.finish(random.choice([
                f'不要打扰 {player1_name} 和 {player2_name} 的决斗啊！',
                '给我好好做好一个观众！不然list(bot.config.nickname)[0]就要生气了',
                f'不要捣乱啊baka{nickname}！'
            ]), at_sender=True)
        nickname = player1_name if rs_player[event.group_id]["next"] == rs_player[event.group_id][1] else player2_name
        await shot.finish(f'你的左轮不是连发的！该 {nickname} 开枪了')
    if rs_player[event.group_id]['bullet'][rs_player[event.group_id]['index']] != 1:
        await shot.send(Message(random.choice([
            '呼呼，没有爆裂的声响，你活了下来',
            '虽然黑洞洞的枪口很恐怖，但好在没有子弹射出来，你活下来了',
            '\"咔\"，你没死，看来运气不错',
        ]) + f'\n下一枪中弹的概率'
             f'：{str(float((rs_player[event.group_id]["bullet_num"])) / float(rs_player[event.group_id]["null_bullet_num"] - 1 + rs_player[event.group_id]["bullet_num"]) * 100)[:5]}%\n'
             f'轮到 {MessageSegment.at(rs_player[event.group_id][1] if event.user_id == rs_player[event.group_id][2] else rs_player[event.group_id][2])}了'))
        rs_player[event.group_id]["null_bullet_num"] -= 1
        rs_player[event.group_id]['next'] = rs_player[event.group_id][1] if \
            event.user_id == rs_player[event.group_id][2] else rs_player[event.group_id][2]
        rs_player[event.group_id]['time'] = time.time()
        rs_player[event.group_id]['index'] += 1
    else:
        await shot.send(random.choice([
            '\"嘭！\"，你直接去世了',
            '眼前一黑，你直接穿越到了异世界...(死亡)',
            '终究还是你先走一步...',
        ]) + f'\n第 {rs_player[event.group_id]["index"] + 1} 发子弹送走了你...', at_sender=True)
        win_name = player1_name if event.user_id == rs_player[event.group_id][2] else player2_name
        await asyncio.sleep(0.5)
        await shot.send(f'这场对决是 {win_name} 胜利了')
        await end_game(bot, event)


async def end_game(bot: Bot, event: GroupMessageEvent):
    global rs_player, player_data
    player1_name = rs_player[event.group_id]['player1']
    player2_name = rs_player[event.group_id]['player2']
    if rs_player[event.group_id]['next'] == rs_player[event.group_id][1]:
        win_user_id = rs_player[event.group_id][2]
        lose_user_id = rs_player[event.group_id][1]
        win_name = player2_name
        lose_name = player1_name
    else:
        win_user_id = rs_player[event.group_id][1]
        lose_user_id = rs_player[event.group_id][2]
        win_name = player1_name
        lose_name = player2_name
    rand = random.randint(0, 5)
    gold = rs_player[event.group_id]['money']
    fee = int(gold * float(rand) / 100)
    fee = 1 if fee < 1 and rand != 0 else fee
    player_data = end_handle(player_data, win_user_id, lose_user_id, event.group_id, gold, fee)
    win_user = player_data[str(event.group_id)][str(win_user_id)]
    lose_user = player_data[str(event.group_id)][str(lose_user_id)]
    bullet_str = ''
    for x in rs_player[event.group_id]['bullet']:
        bullet_str += '__ ' if x == 0 else '| '
    print(f'俄罗斯轮盘：胜者：{win_name} - 败者：{lose_name} - 金币：{gold}')
    await bot.send(event, message=f'结算：\n'
                                  f'\t胜者：{win_name}\n'
                                  f'\t赢取金币：{gold - fee}\n'
                                  f'\t累计胜场：{win_user["win_count"]}\n'
                                  f'\t累计赚取金币：{win_user["make_gold"]}\n'
                                  f'-------------------\n'
                                  f'\t败者：{lose_name}\n'
                                  f'\t输掉金币：{gold}\n'
                                  f'\t累计败场：{lose_user["lose_count"]}\n'
                                  f'\t累计输掉金币：{lose_user["lose_gold"]}\n'
                                  f'-------------------\n'
                                  f'哼哼，{list(bot.config.nickname)[0]}从中收取了 {float(rand)}%({fee}金币) 作为手续费！\n'
                                  f'子弹排列：{bullet_str[:-1]}')
    rs_player[event.group_id] = {}
    with open(file, 'w', encoding='utf8') as f:
        json.dump(player_data, f, ensure_ascii=False, indent=4)


@record.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    global player_data
    player_is_exists(event)
    user = player_data[str(event.group_id)][str(event.user_id)]
    await record.send(f'俄罗斯轮盘\n'
                      f'胜利场次：{user["win_count"]}\n'
                      f'失败场次：{user["lose_count"]}\n'
                      f'赚取金币：{user["make_gold"]}\n'
                      f'输掉金币：{user["lose_gold"]}', at_sender=True)


@rssian_rank.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    global player_data
    if state["_prefix"]["raw_command"] in ['金币排行']:
        await rssian_rank.finish(await rank(player_data, event.group_id, 'gold_rank'))
    if state["_prefix"]["raw_command"] in ['胜场排行', '胜利排行']:
        await rssian_rank.finish(await rank(player_data, event.group_id, 'win_rank'))
    if state["_prefix"]["raw_command"] in ['败场排行', '失败排行']:
        await rssian_rank.finish(await rank(player_data, event.group_id, 'lose_rank'))
    if state["_prefix"]["raw_command"] == '欧洲人排行':
        await rssian_rank.finish(await rank(player_data, event.group_id, 'make_gold'))
    if state["_prefix"]["raw_command"] == '慈善家排行':
        await rssian_rank.finish(await rank(player_data, event.group_id, 'lose_gold'))


@my_gold.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    global player_data
    player_is_exists(event)
    gold = player_data[str(event.group_id)][str(event.user_id)]['gold']
    await my_gold.send(f'你还有 {gold} 枚金币', at_sender=True)


# 随机子弹排列
def random_bullet(num: int) -> list:
    bullet_lst = [0, 0, 0, 0, 0, 0, 0]
    for i in random.sample([0, 1, 2, 3, 4, 5, 6], num):
        bullet_lst[i] = 1
    return bullet_lst


def player_is_exists(event: GroupMessageEvent) -> dict:
    global player_data
    user_id = str(event.user_id)
    group_id = str(event.group_id)
    nickname = event.sender.card if event.sender.card else event.sender.nickname
    if group_id not in player_data.keys():
        player_data[group_id] = {}
    if user_id not in player_data[group_id].keys():
        player_data[group_id][user_id] = {
            'user_id': user_id,
            'group_id': group_id,
            'nickname': nickname,
            'gold': 0,
            'make_gold': 0,
            'lose_gold': 0,
            'win_count': 0,
            'lose_count': 0,
            'is_sign': False,
        }
    return player_data


# 重置每日签到
@scheduler.scheduled_job(
    'cron',
    hour=0,
    minute=0,
)
async def _():
    global player_data
    for group in player_data.keys():
        for user_id in player_data[group].keys():
            player_data[group][user_id]['is_sign'] = False
    print('每日签到重置成功...')


