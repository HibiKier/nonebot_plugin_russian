from nonebot import on_command, require
from nonebot.adapters.onebot.v11 import (
    GROUP,
    Bot,
    GroupMessageEvent,
    MessageSegment,
    Message,
)
from nonebot.typing import T_State
from nonebot.params import Depends, CommandArg, State
from .utils import is_number, get_message_at
from nonebot.log import logger
from .data_source import russian_manager, max_bet_gold


__zx_plugin_name__ = "俄罗斯轮盘"

__plugin_usage__ = """俄罗斯轮盘帮助：
    开启游戏：装弹 [子弹数] ?[金额](默认200金币) ?[at](指定决斗对象，为空则所有群友都可接受决斗)
        示例：装弹 1 10
    接受对决：接受对决/拒绝决斗
    开始对决：开枪 ?[子弹数](默认1)（轮流开枪，根据子弹数量连开N枪械，30秒未开枪另一方可使用‘结算’命令结束对决并胜利）
    结算：结算（当某一方30秒未开枪，可使用该命令强行结束对决并胜利）
    我的战绩：我的战绩
    排行榜：金币排行/胜场排行/败场排行/欧洲人排行/慈善家排行
    【注：同一时间群内只能有一场对决】
"""

scheduler = require("nonebot_plugin_apscheduler").scheduler


sign = on_command("轮盘签到", permission=GROUP, priority=5, block=True)

russian = on_command(
    "俄罗斯轮盘", aliases={"装弹", "俄罗斯转盘"}, permission=GROUP, priority=5, block=True
)

accept = on_command(
    "接受对决", aliases={"接受决斗", "接受挑战"}, permission=GROUP, priority=5, block=True
)

refuse = on_command(
    "拒绝对决", aliases={"拒绝决斗", "拒绝挑战"}, permission=GROUP, priority=5, block=True
)

shot = on_command(
    "开枪", aliases={"咔", "嘭", "嘣"}, permission=GROUP, priority=5, block=True
)

settlement = on_command("结算", permission=GROUP, priority=5, block=True)

record = on_command("我的战绩", permission=GROUP, priority=5, block=True)

russian_rank = on_command(
    "胜场排行",
    aliases={"金币排行", "胜利排行", "败场排行", "失败排行", "欧洲人排行", "慈善家排行"},
    permission=GROUP,
    priority=5,
    block=True,
)

my_gold = on_command("我的金币", permission=GROUP, priority=5, block=True)


@sign.handle()
async def _(event: GroupMessageEvent):
    msg, gold = russian_manager.sign(event)
    await sign.send(msg, at_sender=True)
    if gold != -1:
        logger.info(f"USER {event.user_id} | GROUP {event.group_id} 获取 {gold} 金币")


@accept.handle()
async def _(event: GroupMessageEvent):
    msg = russian_manager.accept(event)
    await accept.send(msg, at_sender=True)


@refuse.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    msg = await russian_manager.refuse(bot, event)
    await refuse.send(msg, at_sender=True)


@settlement.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    msg = russian_manager.settlement(event)
    await settlement.send(msg, at_sender=True)
    await russian_manager.end_game(bot, event)


async def get_bullet_num(
    event: GroupMessageEvent, arg: Message = CommandArg(), state: T_State = State()
):
    msg = arg.extract_plain_text().strip()
    if state["bullet_num"]:
        return state
    if msg in ["取消", "算了"]:
        await russian.finish("已取消操作...")
    try:
        if russian_manager.check_game_is_start(event.group_id):
            await russian.finish("决斗已开始...", at_sender=True)
    except KeyError:
        pass
    if not is_number(msg):
        await russian.reject("输入子弹数量必须是数字啊喂！")
    if int(msg) < 1 or int(msg) > 6:
        await russian.reject("子弹数量必须大于0小于7！")
    return {**state, "bullet_num": int(msg)}


@russian.handle()
async def _(
    bot: Bot,
    event: GroupMessageEvent,
    state: T_State = State(),
    arg: Message = CommandArg(),
):
    msg = arg.extract_plain_text().strip()
    if msg == "帮助":
        await russian.finish(__plugin_usage__)
    try:
        _msg = await russian_manager.check_current_game(bot, event)
    except KeyError:
        pass
    if msg:
        msg = msg.split()
        if len(msg) == 1:
            msg = msg[0]
            if is_number(msg) and not (int(msg) < 1 or int(msg) > 6):
                state["bullet_num"] = int(msg)
        else:
            money = msg[1].strip()
            msg = msg[0].strip()
            if is_number(msg) and not (int(msg) < 1 or int(msg) > 6):
                state["bullet_num"] = int(msg)
            if is_number(money) and 0 < int(money) <= max_bet_gold:
                state["money"] = int(money)
    state["at"] = get_message_at(event.json())


@russian.got("bullet_num", prompt="请输入装填子弹的数量！(最多6颗)")
async def _(
    bot: Bot, event: GroupMessageEvent, state: T_State = Depends(get_bullet_num)
):
    bullet_num = state["bullet_num"]
    at_ = state["at"]
    money = state["money"] if state.get("money") else 200
    user_money = russian_manager.get_user_data(event)["gold"]
    if bullet_num < 0 or bullet_num > 6:
        await russian.reject("子弹数量必须大于0小于7！速速重新装弹！")
    if money > max_bet_gold:
        await russian.finish(f"太多了！单次金额不能超过{max_bet_gold}！", at_sender=True)
    if money > user_money:
        await russian.finish("你没有足够的钱支撑起这场挑战", at_sender=True)

    player1_name = event.sender.card or event.sender.nickname

    if at_:
        at_ = at_[0]
        at_player_name = await bot.get_group_member_info(
            group_id=event.group_id, user_id=int(at_)
        )
        at_player_name = (
            at_player_name["card"]
            if at_player_name["card"]
            else at_player_name["nickname"]
        )
        msg = (
            f"{player1_name} 向 {MessageSegment.at(at_)} 发起了决斗！请 {at_player_name} 在30秒内回"
            f"复‘接受对决’ or ‘拒绝对决’，超时此次决斗作废！"
        )
    else:
        at_ = 0
        msg = "若30秒内无人接受挑战则此次对决作废【首次游玩请发送 ’俄罗斯轮盘帮助‘ 来查看命令】"

    _msg = russian_manager.ready_game(event, msg, player1_name, at_, money, bullet_num)
    await russian.send(_msg)


@shot.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    count = arg.extract_plain_text().strip()
    if is_number(count):
        count = int(count)
        if count > 7 - russian_manager.get_current_bullet_index(event):
            await shot.finish(
                f"你不能开{count}枪，大于剩余的子弹数量，"
                f"剩余子弹数量：{7 - russian_manager.get_current_bullet_index(event)}"
            )
    else:
        count = 1
    await russian_manager.shot(bot, event, count)


@record.handle()
async def _(event: GroupMessageEvent):
    user = russian_manager.get_user_data(event)
    await record.send(
        f"俄罗斯轮盘\n"
        f'胜利场次：{user["win_count"]}\n'
        f'失败场次：{user["lose_count"]}\n'
        f'赚取金币：{user["make_gold"]}\n'
        f'输掉金币：{user["lose_gold"]}',
        at_sender=True,
    )


@russian_rank.handle()
async def _(event: GroupMessageEvent, state: T_State = State()):
    msg = await russian_manager.rank(state["_prefix"]["raw_command"], event.group_id)
    await russian_rank.send(msg)


@my_gold.handle()
async def _(event: GroupMessageEvent):
    gold = russian_manager.get_user_data(event)["gold"]
    await my_gold.send(f"你还有 {gold} 枚金币", at_sender=True)


# 重置每日签到
@scheduler.scheduled_job(
    "cron",
    hour=0,
    minute=0,
)
async def _():
    russian_manager.reset_gold()
    logger.info("每日轮盘签到重置成功...")
