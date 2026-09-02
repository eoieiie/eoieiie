"""컨트리뷰션 격자를 SVG로 그린다. 글자 없음, 잔디만."""
import json, os, subprocess, sys

CELL, GAP, RADIUS = 11, 3, 2
PAD = 16
# 라이트/다크를 따라가지 않고 어두운 배경으로 고정한다.
# 흰 배경에 얹으면 눈이 부시고, 잔디 초록도 다크에서 더 선명하다.
BG, BORDER = "#0d1117", "#21262d"
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

# 프로필 설정의 "Include private contributions" 가 켜져 있으면
# 공개 조회(user(login:))로도 비공개 기여가 총계에 포함된다. 그래서 PAT가 필요 없다.
# 그 설정을 끄면 공개 기여만 잡히므로, 그때는 본인 PAT를 넣고 viewer 조회로 바꿔야 한다.
QUERY = """
{ user(login: "%s") { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date contributionCount } } } } } }
"""

def fetch(user):
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY % user}"],
                         capture_output=True, text=True, check=True).stdout
    cal = json.loads(out)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    print(f"기여 {cal['totalContributions']}건", file=sys.stderr)
    return [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]


def levels(weeks):
    """0이 아닌 값의 사분위로 단계를 나눈다. max 기준으로 자르면 대부분 1단계로 몰린다."""
    vals = sorted(c for w in weeks for c in w if c > 0)
    if not vals:
        return lambda c: 0
    q = [vals[int(len(vals) * p)] for p in (0.25, 0.5, 0.75)]
    def lv(c):
        if c <= 0: return 0
        if c <= q[0]: return 1
        if c <= q[1]: return 2
        if c <= q[2]: return 3
        return 4
    return lv

def build(weeks):
    lv = levels(weeks)
    gw = len(weeks) * (CELL + GAP) - GAP
    gh = 7 * (CELL + GAP) - GAP
    w, h = gw + PAD * 2, gh + PAD * 2
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="contribution graph">',
        "<style>rect{shape-rendering:geometricPrecision}</style>",
        f'<rect x="0" y="0" width="{w}" height="{h}" rx="8" fill="{BG}" stroke="{BORDER}"/>',
    ]
    for x, week in enumerate(weeks):
        # 물결이 왼쪽에서 오른쪽으로 지나간다. 열마다 시작을 조금씩 늦춘다.
        delay = round(x * 0.075, 3)
        for y, count in enumerate(week):
            l = lv(count)
            px, py = PAD + x * (CELL + GAP), PAD + y * (CELL + GAP)
            cell = (f'<rect x="{px}" y="{py}" width="{CELL}" height="{CELL}" rx="{RADIUS}" '
                    f'fill="{PALETTE[l]}"')
            if l == 0:
                out.append(cell + "/>")
                continue
            # 기여가 있는 칸만 은은하게 밝아졌다 돌아온다
            out.append(
                cell + '>'
                f'<animate attributeName="opacity" values="1;0.45;1" dur="9s" '
                f'begin="{delay}s" calcMode="spline" keyTimes="0;0.08;0.36" '
                f'keySplines=".4 0 .2 1;.4 0 .2 1" repeatCount="indefinite"/></rect>'
            )
    out.append("</svg>")
    return "\n".join(out)

if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "eoieiie"
    dest = sys.argv[2] if len(sys.argv) > 2 else "dist/grid.svg"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    svg = build(fetch(user))
    with open(dest, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {dest} ({len(svg)} bytes)")
