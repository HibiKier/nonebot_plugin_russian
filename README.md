# nonebot_plugin_russian

## 介绍

俄罗斯轮盘，通过每日'轮盘签到'来获取金币，然后以金币作为赌注，通过'装弹'来对其他人发起决斗，轮流开枪直到运气不好的人先去世。

## 详细玩法

  ```
    获取金币：轮盘签到
    
    开启游戏：装弹 [子弹数] [金额](默认200金币) [at](指定决斗对象，为空则所有群友都可接受决斗)
            示例：装弹 1 10
            
    接受对决：接受对决/接受挑战/拒绝决斗/拒绝挑战
    
    开始对决：开枪/咔/嘭/嘣 [子弹数](默认1)（轮流开枪，根据子弹数连开N枪，30秒未开枪另一方可使用‘结算’命令结束对决并胜利）
    
    结算：结算（当某一方30秒未开枪，可使用该命令强行结束对决并胜利）
    
    我的战绩：我的战绩
    
    我的金币：我的金币
    
    排行榜：金币排行/胜场排行/败场排行/欧洲人排行/慈善家排行
    【注：同一时间群内只能有一场对决】
  ```

## 配置

  ```
  1.在.env文件中添加对应 属性，以下为默认值
  
      RUSSIAN_PATH = ''         # 数据存储路径，默认路径是此插件目录下

      SIGN_GOLD = [1, 100]      # 每日签到可得到的金币范围

      MAX_BET_GOLD = 1000       # 赌注的最大上限（防止直接梭哈白给天台见）
  
  2.在bot入口文件添加
    nonebot.load_plugin("nonebot_plugin_russian")
  ```
  
## 更新

### 2022/2/15

  * fit beat1 [@pull 9](https://github.com/HibiKier/nonebot_plugin_russian/pull/9)

### 2022/1/29

  * 适配nonebot2.beat1

### 2021/7/4

  * 当BOT未配置NICKNAME时，将结算字符串中的bot名称改成 ‘本裁判’
  
## 部分效果展示

![](https://github.com/HibiKier/nonebot_plugin_russian/blob/main/docs/0.png)

![](https://github.com/HibiKier/nonebot_plugin_russian/blob/main/docs/1.png)
