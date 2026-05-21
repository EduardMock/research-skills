#!/usr/bin/env bash
# Reproduces the "Verified reference numbers" table in SKILL.md.
# Runs three small g-xTB jobs and prints the headline numbers.
#
# Resolves the binary in this order:
#   1. $GXTB_BIN
#   2. $XTB_BIN
#   3. `xtb` on PATH
set -euo pipefail

XTB="${GXTB_BIN:-${XTB_BIN:-$(command -v xtb || true)}}"
[[ -n "$XTB" && -x "$XTB" ]] || { echo "xtb binary not found. Set GXTB_BIN or put g-xTB's xtb on PATH." >&2; exit 1; }

WORK=$(mktemp -d -t gxtb_smoke_XXXX)
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

cat > h2o.xyz <<'EOF'
3
water
O   0.00000000   0.00000000   0.11779000
H   0.00000000   0.75545000  -0.47116000
H   0.00000000  -0.75545000  -0.47116000
EOF

cat > nh4.xyz <<'EOF'
5
ammonium cation
N    0.000000    0.000000    0.000000
H    0.583000    0.583000    0.583000
H   -0.583000   -0.583000    0.583000
H   -0.583000    0.583000   -0.583000
H    0.583000   -0.583000   -0.583000
EOF

# Each job in its own subdir so xtbrestart/charges/wbo don't collide.
run() {
    local tag="$1"; shift
    local sub="$WORK/$tag"; mkdir -p "$sub"
    cp "$1" "$sub/"; shift
    ( cd "$sub" && "$XTB" "$@" ) > "$sub/out.log" 2>&1 || {
        echo "FAIL $tag — see $sub/out.log" >&2
        tail -20 "$sub/out.log" >&2
        return 1
    }
    echo "$sub"
}

d1=$(run h2o_sp      h2o.xyz h2o.xyz --gxtb)
d2=$(run h2o_opt     h2o.xyz h2o.xyz --gxtb --opt)
d3=$(run nh4_charged nh4.xyz nh4.xyz --gxtb --chrg 1)

printf '\n%-22s %-20s %-10s\n' SYSTEM "E(total) / Eh" GAP/eV
printf -- '-%.0s' {1..55}; echo
for d in "$d1" "$d2" "$d3"; do
    e=$(grep -E 'TOTAL ENERGY' "$d/out.log" | tail -1 | awk '{print $4}')
    g=$(grep -E 'HOMO-LUMO gap' "$d/out.log" | tail -1 | awk '{print $4}')
    printf '%-22s %-20s %-10s\n' "$(basename "$d")" "${e:-n/a}" "${g:-n/a}"
done

echo
echo "OK — all three jobs finished with 'normal termination of xtb'."
