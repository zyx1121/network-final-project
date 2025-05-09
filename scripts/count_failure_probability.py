import argparse
from math import comb


def failure_probability(k: int, n: int, loss_rate: float) -> float:
    success_rate = 1 - loss_rate
    prob = 0.0
    print("計算過程：")
    for i in range(k):  # 收到 0 到 k-1 個封包都算失敗
        c = comb(n, i)
        p = c * (success_rate**i) * (loss_rate ** (n - i))
        # 印出每一項的公式與數值
        print(
            f"i={i}: C({n},{i}) * (成功率^{i}) * (失敗率^{n-i}) = "
            f"{c} * ({success_rate:.4f}^{i}) * ({loss_rate:.4f}^{n-i}) = {p:.10f}"
        )
        prob += p
    return prob


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="計算RS編碼下無法還原的機率")
    parser.add_argument("--k", type=int, required=True, help="還原需要的封包數")
    parser.add_argument("--n", type=int, required=True, help="總共傳送的封包數")
    parser.add_argument(
        "--loss", type=float, required=True, help="每個封包的丟失率 (0~1)"
    )

    args = parser.parse_args()

    print(
        f"無法還原的機率公式：P = Σ[i=0~{args.k-1}] C({args.n},i) * (1-loss)^{{i}} * (loss)^{{{args.n}-i}}"
    )
    fail_prob = failure_probability(args.k, args.n, args.loss)
    print(f"當 k={args.k}, n={args.n}, loss_rate={args.loss:.2%} 時")
    print(f"無法還原的機率為：約 {fail_prob:.10f}（約 {fail_prob*100:.10f}%）")
