"""
portfolio.py — 인메모리 포트폴리오 트래커 (페이퍼 트레이딩)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import pandas as pd


@dataclass
class Position:
    market: str
    amount_krw: float          # 투자 금액 (KRW)
    entry_price: float         # 매수 평균 단가
    quantity: float            # 보유 수량
    entry_time: datetime = field(default_factory=datetime.now)

    def current_value(self, current_price: float) -> float:
        return self.quantity * current_price

    def pnl(self, current_price: float) -> float:
        return self.current_value(current_price) - self.amount_krw

    def pnl_pct(self, current_price: float) -> float:
        if self.amount_krw == 0:
            return 0.0
        return (self.pnl(current_price) / self.amount_krw) * 100


class Portfolio:
    """
    페이퍼 트레이딩 포트폴리오.
    실제 주문 없이 가상으로 보유량/손익을 추적.
    """

    def __init__(self, initial_krw: float = 1_000_000):
        self.cash_krw: float = initial_krw          # 가용 현금
        self.positions: dict[str, Position] = {}     # 보유 포지션
        self.trade_history: list[dict] = []          # 거래 이력

    # ── 매수 ──────────────────────────────────────────────
    def buy(self, market: str, amount_krw: float, current_price: float) -> bool:
        if self.cash_krw < amount_krw:
            print(f"  [포트폴리오] 잔고 부족: 필요 {amount_krw:,.0f}원, 보유 {self.cash_krw:,.0f}원")
            return False

        quantity = amount_krw / current_price
        fee = amount_krw * 0.0005  # Upbit 수수료 0.05%

        if market in self.positions:
            # 평균 단가 재계산 (물타기)
            pos = self.positions[market]
            total_qty = pos.quantity + quantity
            total_krw = pos.amount_krw + amount_krw
            pos.entry_price = total_krw / total_qty
            pos.quantity = total_qty
            pos.amount_krw = total_krw
        else:
            self.positions[market] = Position(
                market=market,
                amount_krw=amount_krw,
                entry_price=current_price,
                quantity=quantity,
            )

        self.cash_krw -= (amount_krw + fee)
        self.trade_history.append({
            "time": datetime.now(),
            "type": "BUY",
            "market": market,
            "price": current_price,
            "amount_krw": amount_krw,
            "quantity": quantity,
        })
        print(f"  [매수] {market} @ {current_price:,.0f}원 × {quantity:.6f} = {amount_krw:,.0f}원 (수수료 {fee:.0f}원)")
        return True

    # ── 매도 ──────────────────────────────────────────────
    def sell(self, market: str, current_price: float) -> bool:
        if market not in self.positions:
            print(f"  [포트폴리오] {market} 포지션 없음 (매도 불가)")
            return False

        pos = self.positions[market]
        proceeds = pos.quantity * current_price
        fee = proceeds * 0.0005
        net_proceeds = proceeds - fee
        profit = net_proceeds - pos.amount_krw

        self.cash_krw += net_proceeds
        del self.positions[market]

        self.trade_history.append({
            "time": datetime.now(),
            "type": "SELL",
            "market": market,
            "price": current_price,
            "proceeds_krw": net_proceeds,
            "profit_krw": profit,
        })
        emoji = "🟢" if profit >= 0 else "🔴"
        print(f"  [매도] {market} @ {current_price:,.0f}원 → 수익: {emoji}{profit:+,.0f}원 ({profit/pos.amount_krw*100:+.2f}%)")
        return True

    # ── 수익률 계산 ───────────────────────────────────────
    def calculate_returns(self, current_prices: Optional[dict] = None) -> dict:
        """
        현재 포트폴리오 총 수익률 계산.
        
        Args:
            current_prices: {market: price} 딕셔너리 (없으면 매수가 기준)
        
        Returns:
            {
                "total_value_krw": float,
                "cash_krw": float,
                "positions_value_krw": float,
                "total_pnl_krw": float,
                "total_pnl_pct": float,
                "positions": list[dict]
            }
        """
        current_prices = current_prices or {}
        positions_detail = []
        total_invested = 0.0
        total_current = 0.0

        for market, pos in self.positions.items():
            price = current_prices.get(market, pos.entry_price)
            cur_val = pos.current_value(price)
            pnl = pos.pnl(price)
            pnl_pct = pos.pnl_pct(price)
            total_invested += pos.amount_krw
            total_current += cur_val
            positions_detail.append({
                "market": market,
                "entry_price": pos.entry_price,
                "current_price": price,
                "quantity": pos.quantity,
                "invested_krw": pos.amount_krw,
                "current_value_krw": cur_val,
                "pnl_krw": pnl,
                "pnl_pct": pnl_pct,
            })

        total_value = self.cash_krw + total_current
        total_pnl = total_current - total_invested
        initial = self.cash_krw + total_invested  # 현금 + 투자 원금
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

        return {
            "total_value_krw": total_value,
            "cash_krw": self.cash_krw,
            "positions_value_krw": total_current,
            "total_invested_krw": total_invested,
            "total_pnl_krw": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "positions": positions_detail,
            "trade_count": len(self.trade_history),
        }

    def print_status(self, current_prices: Optional[dict] = None):
        """포트폴리오 현황 출력."""
        r = self.calculate_returns(current_prices)
        print("\n" + "═" * 55)
        print("  📊 포트폴리오 현황 (페이퍼 트레이딩)")
        print("═" * 55)
        print(f"  현금 잔고    : {r['cash_krw']:>15,.0f} 원")
        print(f"  보유 평가액  : {r['positions_value_krw']:>15,.0f} 원")
        print(f"  총 자산      : {r['total_value_krw']:>15,.0f} 원")

        if r["total_invested_krw"] > 0:
            pnl_emoji = "🟢" if r["total_pnl_krw"] >= 0 else "🔴"
            print(f"  투자 원금    : {r['total_invested_krw']:>15,.0f} 원")
            print(f"  총 손익      : {pnl_emoji} {r['total_pnl_krw']:>+13,.0f} 원  ({r['total_pnl_pct']:+.2f}%)")

        if r["positions"]:
            print("\n  ── 보유 종목 ──────────────────────────────────")
            for p in r["positions"]:
                emoji = "🟢" if p["pnl_pct"] >= 0 else "🔴"
                print(f"  {p['market']:<12} 수익률: {emoji}{p['pnl_pct']:>+6.2f}%  "
                      f"({p['pnl_krw']:>+10,.0f}원)")
        else:
            print("\n  보유 종목 없음")

        print(f"\n  총 거래 횟수 : {r['trade_count']}회")
        print("═" * 55)
