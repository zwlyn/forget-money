'''
Author: zwlyn 1666013677@qq.com
Date: 2022-10-18 19:50:39
LastEditors: zwlyn 1666013677@qq.com
'''
import backtrader as bt
import backtrader as bt
from backtrader.indicators import EMA
import json
import datetime
import os.path
import sys
import backtrader as bt
from backtrader.indicators import EMA


class Simple(bt.Strategy):
    """
    简单策略：
    价格连续2次下降:buy
    持有5天后:sell
    """
    name = 'simple'

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None

    def log(self, txt, dt=None):
        ''' 日志函数，用于统一输出日志格式 '''
        dt = dt or self.datas[0].datetime.date(0)
        print('{}, {}'.format(dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:  # 如订单已被处理，则不用做任何事情
            return

        if order.status in [order.Completed]:  # 检查订单是否完成
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)

            self.bar_executed = len(self)

        # 订单因为缺少资金之类的原因被拒绝执行
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """
        交易成果

        Arguments:
            trade {object} -- 交易状态
        """
        if not trade.isclosed:
            return

        # 显示交易的毛利率和净利润
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        if self.order:  # 是否正在下单，如果是的话不能提交第二次订单
            return
        if not self.position:  # 是否已经买入
            if self.dataclose[0] < self.dataclose[-1]:
                if self.dataclose[-1] < self.dataclose[-2]:
                    self.log('BUY CREATE, %.2f' % self.dataclose[0])
                    self.order = self.buy()

        else:
            if len(self) >= (self.bar_executed + 5):
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()

    def stop(self):
        self.log(u'Ending Value %.2f' %
                 (self.broker.getvalue()))


class Macd(bt.Strategy):
    """
    Macd策略
    """
    params = (
        ('maperiod', 15),
    )
    name = 'macd'

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    @staticmethod
    def percent(today, yesterday):
        return float(today - yesterday) / today

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.volume = self.datas[0].volume

        self.order = None
        self.buyprice = None
        self.buycomm = None

        me1 = EMA(self.data, period=12)
        me2 = EMA(self.data, period=26)
        self.macd = me1 - me2
        self.signal = EMA(self.macd, period=9)

        bt.indicators.MACDHisto(self.data)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.bar_executed_close = self.dataclose[0]
            else:
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        self.log('Close, %.2f' % self.dataclose[0])
        if self.order:
            return

        if not self.position:
            condition1 = self.macd[-1] - self.signal[-1]
            condition2 = self.macd[0] - self.signal[0]
            if condition1 < 0 and condition2 > 0:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()

        else:
            condition = (
                self.dataclose[0] - self.bar_executed_close) / self.dataclose[0]
            if condition > 0.1 or condition < -0.1:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()


class Kdj(bt.Strategy):
    name = 'kdj'

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.volume = self.datas[0].volume

        self.order = None
        self.buyprice = None
        self.buycomm = None

        # 9个交易日内最高价
        self.high_nine = bt.indicators.Highest(self.data.high, period=9)
        # 9个交易日内最低价
        self.low_nine = bt.indicators.Lowest(self.data.low, period=9)
        # 计算rsv值
        self.rsv = 100 * bt.DivByZero(
            self.data_close - self.low_nine, self.high_nine - self.low_nine, zero=None
        )
        # 计算rsv的3周期加权平均值，即K值
        self.K = bt.indicators.EMA(self.rsv, period=3, plot=False)
        # D值=K值的3周期加权平均值
        self.D = bt.indicators.EMA(self.K, period=3, plot=False)
        # J=3*K-2*D
        self.J = 3 * self.K - 2 * self.D

        # MACD策略参数
        me1 = EMA(self.data, period=12)
        me2 = EMA(self.data, period=26)
        self.macd = me1 - me2
        self.signal = EMA(self.macd, period=9)
        bt.indicators.MACDHisto(self.data)

    @staticmethod
    def percent(today, yesterday):
        """
        差值占比

        Arguments:
            today {float} -- 今天的数据
            yesterday {float} -- 昨天的数据

        Returns:
            float -- 差值占比
        """
        return float(today - yesterday) / today

    def next(self):
        if not self.position:
            # 买入基于MACD策略
            condition1 = self.macd[-1] - self.signal[-1]
            condition2 = self.macd[0] - self.signal[0]
            if condition1 < 0 and condition2 > 0:
                self.order = self.buy()

        else:
            # 卖出基于KDJ策略
            condition1 = self.J[-1] - self.D[-1]
            condition2 = self.J[0] - self.D[0]
            if condition1 > 0 or condition2 < 0:
                self.order = self.sell()


class AvgProfit(bt.Strategy):
    name = 'avgProfit'
    params = (
        ('code', 0),
        ('profits', [])
    )

    def log(self, txt, dt=None):
        """ Logging function fot this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.isoformat(), txt))

    @staticmethod
    def percent(today, yesterday):
        return float(today - yesterday) / today

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.volume = self.datas[0].volume

        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.params.profits = []

        me1 = EMA(self.data, period=12)
        me2 = EMA(self.data, period=26)
        self.macd = me1 - me2
        self.signal = EMA(self.macd, period=9)

        bt.indicators.MACDHisto(self.data)

    def notify_order(self, order):
        # 交易状态处理
        # Python实用宝典
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    "BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )

                # 记录买入价格
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.bar_executed_close = self.dataclose[0]
            else:
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                # 收益率计算
                profit_rate = float(order.executed.price -
                                    self.buyprice)/float(self.buyprice)
                # 存入策略变量
                self.params.profits.append(profit_rate)

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log("OPERATION PROFIT, GROSS %.2f, NET %.2f" %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        self.log("Close, %.2f" % self.dataclose[0])
        if self.order:
            return

        if not self.position:
            condition1 = self.macd[-1] - self.signal[-1]
            condition2 = self.macd[0] - self.signal[0]
            if condition1 < 0 and condition2 > 0:
                self.log("BUY CREATE, %.2f" % self.dataclose[0])
                self.order = self.buy()

        else:
            condition = (self.dataclose[0] - self.bar_executed_close) / self.dataclose[
                0
            ]
            if condition > 0.1 or condition < -0.1:
                self.log("SELL CREATE, %.2f" % self.dataclose[0])
                self.order = self.sell()


class Harami(bt.Strategy):
    name = 'harami'

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.dataopen = self.datas[0].open
        self.volume = self.datas[0].volume

        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.params.profits = []

        self.sma20 = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=20)

        me1 = EMA(self.data, period=12)
        me2 = EMA(self.data, period=26)
        self.macd = me1 - me2
        self.signal = EMA(self.macd, period=9)

        bt.indicators.MACDHisto(self.data)

    def log(self, txt, dt=None):
        """ Logging function fot this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        # print('%s, %s' % (dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    "BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.bar_executed_close = self.dataclose[0]
            else:
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                temp = float(order.executed.price -
                             self.buyprice)/float(self.buyprice)
                self.params.profits.append(temp)

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.bar_executed = len(self)
        self.log("OPERATION PROFIT, GROSS %.2f, NET %.2f" %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        self.log("Close, %.2f" % self.dataclose[0])
        if self.order:
            return
        if not self.position:
            # condition1 = self.sma20[0] > self.dataclose[0]
            if self.dataclose[-1] < self.dataopen[-1]:
                harami = (
                    self.datahigh[0] < self.dataopen[-1]
                    and self.datalow[0] > self.dataclose[-1]
                )
            else:
                harami = (
                    self.datahigh[0] < self.dataclose[-1]
                    and self.datalow[0] > self.dataopen[-1]
                )

            if harami:
                self.log("BUY CREATE, %.2f" % self.dataclose[0])
                self.order = self.buy()

        else:
            condition = (self.dataclose[0] - self.bar_executed_close) / self.dataclose[
                0
            ]
            if condition > 0.1 or condition < -0.1:
                self.log("SELL CREATE, %.2f" % self.dataclose[0])
                self.order = self.sell()


class Run:
    def __init__(self, strategies=[Simple]):
        self.strategies = strategies
        self.files_path = 'stocks\\'
        self.result = {}
        self.result_file = None
        for st in self.strategies:
            self.runStocks(st)
        self.save_result()
        self.analyse()

    def analyse(self):
        with open(self.result_file, 'r') as f:
            data = json.load(f)
        # 计算
        pos = []
        neg = []
        ten_pos = []
        ten_neg = []
        for result in data:
            res = data[result]
            if res > 0:
                pos.append(res)
            else:
                neg.append(res)

            if res > 0.1:
                ten_pos.append(result)
            elif res < -0.1:
                ten_neg.append(result)

        max_stock = max(data, key=data.get)
        print(f'最高收益的股票： {max_stock}, 达到 {data[max_stock]}')
        print(f'正收益数量: {len(pos)}, 负收益数量:{len(neg)}')
        print(f'+10%数量: {len(ten_pos)}, -10%数量:{len(ten_neg)}')
        print(f'收益10%以上的股票: {ten_pos}')

    def save_result(self):
        now = datetime.datetime.now().strftime('%m%d%H%M')
        self.result_file = '{}-result.json'.format(now)
        print(self.result_file, self.result)
        with open(self.result_file, 'w') as f:
            f.write(json.dumps(self.result, indent=4, ensure_ascii=False))

    def runStocks(self, strategy):
        # 遍历所有股票数据
        for stock in os.listdir(self.files_path):
            modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
            datapath = os.path.join(modpath, self.files_path + stock)
            print(datapath)
            try:
                self.do_strategy(datapath, strategy)
            except Exception as e:
                print(e)

    def do_strategy(self, stock_file, strategy):
        """
        运行策略
        :param stock_file: 股票数据文件位置
        :param result: 回测结果存储变量
        """
        cerebro = bt.Cerebro()

        cerebro.addstrategy(strategy)

        # 加载数据到模型中
        data = bt.feeds.GenericCSVData(
            dataname=stock_file,
            fromdate=datetime.datetime(2010, 1, 1),
            todate=datetime.datetime(2020, 4, 25),
            dtformat='%Y%m%d',
            datetime=2,
            open=3,
            high=4,
            low=5,
            close=6,
            volume=10,
            reverse=True
        )
        cerebro.adddata(data)
        cerebro.broker.setcash(10000)  # 本金10000，每次交易100股
        cerebro.addsizer(bt.sizers.FixedSize, stake=100)
        cerebro.broker.setcommission(commission=0.0005)  # 万五佣金
        cerebro.run()  # 运行策略
        money_left = cerebro.broker.getvalue()  # 剩余本金
        stock_name = stock_file.split('\\')[-1].split('.csv')[0]  # 获取股票名字
        key_name = "{}-{}".format(stock_name, strategy.name)
        # 将最终回报率以百分比的形式返回
        self.result[key_name] = float(money_left - 10000) / 10000


Run([Harami])
