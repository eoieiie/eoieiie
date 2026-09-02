"""컨트리뷰션 격자를 SVG로 그린다. 글자 없음, 잔디만."""
import json, os, subprocess, sys

CELL, GAP, RADIUS = 11, 3, 2
PAD = 16
# 라이트/다크를 따라가지 않고 어두운 배경으로 고정한다.
# 흰 배경에 얹으면 눈이 부시고, 잔디 초록도 다크에서 더 선명하다.
BG, BORDER = "#0d1117", "#21262d"
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

# viewer = 토큰 소유자 본인. 이쪽으로 조회해야 private 레포 기여까지 집계된다.
# user(login:) 로 조회하면 public 기여만 잡혀서 실제 활동량과 크게 어긋난다.
VIEWER_QUERY = """
{ viewer { login contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date contributionCount } } } } } }
"""
USER_QUERY = """
{ user(login: "%s") { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date contributionCount } } } } } }
"""

def _run(query):
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={query}"],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)["data"]

def fetch(user):
    """본인 토큰이면 viewer로, 아니면(봇 토큰 등) user(login:)으로 떨어진다."""
    try:
        d = _run(VIEWER_QUERY)["viewer"]
        if d["login"].lower() == user.lower():
            cal = d["contributionsCollection"]["contributionCalendar"]
            print(f"viewer 조회 (private 포함): {cal['totalContributions']}", file=sys.stderr)
            return [[x["contributionCount"] for x in w["contributionDays"]] for w in cal["weeks"]]
    except Exception as e:
        print(f"viewer 조회 실패, user 조회로 폴백: {e}", file=sys.stderr)
    cal = _run(USER_QUERY % user)["user"]["contributionsCollection"]["contributionCalendar"]
    print(f"user 조회 (public만): {cal['totalContributions']}", file=sys.stderr)
    return [[x["contributionCount"] for x in w["contributionDays"]] for w in cal["weeks"]]

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
