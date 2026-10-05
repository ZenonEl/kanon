#!/usr/bin/env bash
# Accept valid EN/RU checklists and refuse malformed ones; regressions must fail when protection is removed.
set -u
cd "$(dirname "$0")/.."
here_root=$(pwd)
fail=0

# Check parser values separately from exit codes.
python3 tests/test_parser.py || fail=1
python3 tests/test_retire.py || fail=1

for f in tests/fixtures/good-en.md tests/fixtures/good-ru.md; do
  if python3 scripts/check-checklist.py "$f" >/dev/null 2>&1; then
    echo "ok    $f accepted"
  else
    echo "ERROR $f should be accepted:"; python3 scripts/check-checklist.py "$f"; fail=1
  fi
done

out=$(python3 scripts/check-checklist.py tests/fixtures/bad-ru.md 2>&1)
if [ $? -eq 0 ]; then
  echo "ERROR bad-ru.md should be rejected"; fail=1
else
  for expect in "empty claim" "nonexistent item" "slots=3"; do
    if echo "$out" | grep -q "$expect"; then
      echo "ok    caught: $expect"
    else
      echo "ERROR not caught: $expect"; echo "$out"; fail=1
    fi
  done
fi

python3 scripts/sweep.py >/dev/null 2>&1 \
  && echo "ok    sweep handles a missing directory" \
  || { echo "ERROR sweep failed without a directory"; fail=1; }

# Hooks must stay silent and exit zero on malformed payloads.
for e in SessionStart PreToolUse Stop; do
  echo '{}' | python3 hooks/kanon-hook.py "$e" >/dev/null 2>&1 \
    && echo "ok    hook $e handles empty input" \
    || { echo "ERROR hook $e failed"; fail=1; }
done
echo 'мусор' | python3 hooks/kanon-hook.py PreToolUse >/dev/null 2>&1 \
  && echo "ok    hook handles malformed input" || { echo "ERROR hook failed on malformed input"; fail=1; }

# Hook exit codes are always zero; assert actual reminder and outstanding-item output.
hb=$(mktemp -d); mkdir -p "$hb/_kanon"
cat > "$hb/_kanon/h.md" <<'HOOKFIX'
---
task: t
opened: 2026-09-02
closed: null
slots: null
source: -
---
## Gathered
- x · y
## Acceptance
- [ ] 7. незакрытый пункт · check: тест
HOOKFIX
here=$(pwd)
out=$( cd "$hb" && echo '{}' | python3 "$here/hooks/kanon-hook.py" Stop )
echo "$out" | grep -q '7\.'   && echo "ok    Stop lists an open item"   || { echo "ERROR Stop silent with an open item"; fail=1; }
# PreToolUse and Stop need systemMessage JSON; plain stdout may only reach debug logs.
if echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); assert isinstance(d.get('systemMessage'),str) and d['systemMessage']; assert 'decision' not in d" 2>/dev/null; then
  echo "ok    Stop emits systemMessage JSON without blocking"
else
  echo "ERROR Stop output is not JSON and will not reach its reader"; fail=1
fi
# Exercise SessionStart with stale work so the output-shape assertion cannot pass on silence.
cp "$hb/_kanon/h.md" "$hb/_kanon/stale.md"; touch -d "30 days ago" "$hb/_kanon/stale.md"
ss=$( cd "$hb" && echo '{}' | python3 "$here/hooks/kanon-hook.py" SessionStart )
[ -n "$ss" ] && echo "ok    SessionStart reports stale work" \
  || { echo "ERROR SessionStart silent with a stale checklist"; fail=1; }
case "$ss" in
  "{"*) echo "ERROR SessionStart emits JSON instead of visible plain stdout"; fail=1 ;;
  *)    echo "ok    SessionStart emits plain text" ;;
esac

# Gathering without a checklist must trigger exactly one production reminder.
pb=$(mktemp -d); tr="$pb/tr.jsonl"
for i in 1 2 3 4; do echo '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read"}]}}'; done > "$tr"
sid="selftest-$$"
pay="{\"session_id\":\"$sid\",\"transcript_path\":\"$tr\",\"tool_input\":{\"file_path\":\"$pb/src/a.py\"}}"
first=$( cd "$pb" && echo "$pay" | python3 "$here/hooks/kanon-hook.py" PreToolUse )
second=$( cd "$pb" && echo "$pay" | python3 "$here/hooks/kanon-hook.py" PreToolUse )
[ -n "$first" ] && echo "ok    PreToolUse reminds after gathering without a checklist"   || { echo "ERROR PreToolUse silent after gathering"; fail=1; }
if echo "$first" | python3 -c "import json,sys; d=json.load(sys.stdin); assert isinstance(d.get('systemMessage'),str) and d['systemMessage']; assert 'permissionDecision' not in str(d)" 2>/dev/null; then
  echo "ok    PreToolUse emits systemMessage JSON without permission decisions"
else
  echo "ERROR PreToolUse output is not JSON and will not reach its reader"; fail=1
fi
[ -z "$second" ] && echo "ok    PreToolUse speaks once per session"   || { echo "ERROR PreToolUse repeated in the same session"; fail=1; }
command rm -rf "$hb" "$pb" "${TMPDIR:-/tmp}/kanon-$(id -u)"

# An item-shaped line that cannot parse must produce an error.
mb=$(mktemp -d)
cat > "$mb/malformed.md" <<'MALFORMED'
---
task: t
opened: 2026-09-02
closed: null
slots: null
source: -
---
## Gathered
- x · y
## Приёмка / Acceptance
- [x] 1. res · proof: коммит a1b2c3d
- [ ] без номера · check: скрин
MALFORMED
if python3 scripts/check-checklist.py "$mb/malformed.md" 2>&1 | grep -q 'not parsed'; then
  echo "ok    unparsed item is reported as an error"
else
  echo "ERROR unparsed item silently lost"; fail=1
fi
cat > "$mb/bilingual.md" <<'BILINGUAL'
---
task: t
opened: 2026-09-02
closed: null
slots: null
source: -
---
## Из собранного / Gathered
- x · y
## Приёмка / Acceptance
- [x] 1. res · check: c · proof: коммит a1b2c3d
BILINGUAL
if python3 scripts/check-checklist.py "$mb/bilingual.md" 2>&1 | grep -q '1/1'; then
  echo "ok    bilingual heading recognized"
else
  echo "ERROR bilingual heading not recognized:"
  python3 scripts/check-checklist.py "$mb/bilingual.md"; fail=1
fi
cat > "$mb/noacc.md" <<'NOACC'
---
task: t
opened: 2026-09-02
closed: null
slots: null
source: -
---
## Gathered
- x · y
NOACC
python3 scripts/check-checklist.py "$mb/noacc.md" >/dev/null 2>&1 \
  && { echo "ERROR checklist without Acceptance accepted"; fail=1; } \
  || echo "ok    checklist without Acceptance rejected"

# An existing but empty acceptance section must also fail.
cat > "$mb/emptyacc.md" <<'EMPTYACC'
---
task: t
opened: 2026-09-02
closed: null
slots: null
source: -
---
## Gathered
- x · y
## Acceptance
EMPTYACC
python3 scripts/check-checklist.py "$mb/emptyacc.md" >/dev/null 2>&1 \
  && { echo "ERROR empty Acceptance accepted"; fail=1; } \
  || echo "ok    empty Acceptance rejected"

# Short proof paths and separators within proof remain valid.
cat > "$mb/proofs.md" <<'PROOFS'
---
task: t
opened: 2026-09-02
closed: null
slots: null
source: -
---
## Gathered
- x · y
## Acceptance
- [x] 1. r · check: c · proof: h.png
- [x] 2. r · check: c · proof: out.txt · строка 2
PROOFS
python3 scripts/check-checklist.py "$mb/proofs.md" >/dev/null 2>&1 \
  && echo "ok    path and proof with separators accepted" \
  || { echo "ERROR valid proof rejected:"; python3 scripts/check-checklist.py "$mb/proofs.md"; fail=1; }
command rm -rf "$mb"

# Error severity must remain failing even when user text contains the warning marker.
sb=$(mktemp -d)
cat > "$sb/sev.md" <<'SEV'
---
task: t
opened: 2026-09-02
closed: null
slots: null
source: -
---
## Gathered
- x · y
## Acceptance
- [x] 1. ok · check: c · proof: коммит a1b2c3d
- [ ] (!) 2. срочный · check: c
SEV
python3 scripts/check-checklist.py "$sb/sev.md" >/dev/null 2>&1 \
  && { echo "ERROR item containing (!) returned zero despite a reported error"; fail=1; } \
  || echo "ok    error containing (!) returns one"
command rm -rf "$sb"

# Index-write failure must not suppress the lifetime report.
wb=$(mktemp -d); mkdir -p "$wb/_kanon"
cat > "$wb/_kanon/s.md" <<'STALE'
---
task: заброшенный
opened: 2026-08-01
closed: null
slots: null
source: -
---
## Gathered
- x · y
## Acceptance
- [ ] 1. так и не собрал · check: тест
STALE
touch -d "30 days ago" "$wb/_kanon/s.md"
chmod a-w "$wb/_kanon"
out=$( cd "$wb" && python3 "$(pwd -P >/dev/null; echo "$here_root")/scripts/sweep.py" 2>&1 || true )
chmod u+w "$wb/_kanon"
echo "$out" | grep -q 'STALE' \
  && echo "ok    sweep reports despite unwritable INDEX.md" \
  || { echo "ERROR sweep lost its report:"; echo "$out"; fail=1; }
command rm -rf "$wb"

# Automatic index writes must not follow an unrelated symbolic-link target.
lb=$(mktemp -d); mkdir -p "$lb/_kanon"
echo "не трогать" > "$lb/victim.txt"
ln -s "$lb/victim.txt" "$lb/_kanon/INDEX.md"
cp tests/fixtures/good-ru.md "$lb/_kanon/c.md"
( cd "$lb" && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 ) || true
if [ "$(cat "$lb/victim.txt")" = "не трогать" ]; then
  echo "ok    INDEX.md write refuses symlink targets"
else
  echo "ERROR sweep overwrote a symlink target"; fail=1
fi

# A hard link shares the inode; O_NOFOLLOW alone cannot protect its target.
hl=$(mktemp -d); mkdir -p "$hl/_kanon"
echo "не трогать" > "$hl/victim.txt"
ln "$hl/victim.txt" "$hl/_kanon/INDEX.md"
cp tests/fixtures/good-ru.md "$hl/_kanon/c.md"
( cd "$hl" && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 ) || true
if [ "$(cat "$hl/victim.txt")" = "не трогать" ]; then
  echo "ok    INDEX.md write preserves hard-link targets"
else
  echo "ERROR sweep overwrote a hard-link target"; fail=1
fi
ls "$hl/_kanon"/.INDEX.md.tmp-* >/dev/null 2>&1 \
  && { echo "ERROR temporary index file not removed"; fail=1; } \
  || echo "ok    temporary index file removed"
# Failed replacement must remove its temporary file.
dl=$(mktemp -d); mkdir -p "$dl/_kanon/INDEX.md"
cp tests/fixtures/good-ru.md "$dl/_kanon/c.md"
out_dir=$( cd "$dl" && python3 "$here_root/scripts/sweep.py" 2>&1 || true )
echo "$out_dir" | grep -q 'open' \
  && echo "ok    report survives index-write failure" \
  || { echo "ERROR report lost on index-write failure"; fail=1; }
if ls "$dl/_kanon"/.INDEX.md.tmp-* >/dev/null 2>&1; then
  echo "ERROR temporary file retained after failed replacement"; fail=1
else
  echo "ok    temporary file removed after failed replacement"
fi
command rm -rf "$dl"

command rm -rf "$hl"
out_sym=$( cd "$lb" && python3 "$here_root/scripts/sweep.py" 2>&1 || true )
echo "$out_sym" | grep -q 'open\|STALE' \
  && echo "ok    report survives refused index write" \
  || { echo "ERROR report lost with a symlink"; fail=1; }
command rm -rf "$lb"

# A stale active checklist suppresses a duplicate production reminder.
nb=$(mktemp -d); mkdir -p "$nb/_kanon"; tr2="$nb/tr.jsonl"
cat > "$nb/_kanon/s.md" <<'NAG'
---
task: всё доказано, closed не проставлен
opened: 2026-08-01
closed: null
slots: null
source: -
---
## Gathered
- x · y
## Acceptance
- [x] 1. r · check: c · proof: коммит a1b2c3d
NAG
touch -d "28 days ago" "$nb/_kanon/s.md"
for i in 1 2 3 4; do echo '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read"}]}}'; done > "$tr2"
sid2="selftest-nag-$$"
pay2="{\"session_id\":\"$sid2\",\"transcript_path\":\"$tr2\",\"tool_input\":{\"file_path\":\"$nb/src/a.py\"}}"
nag=$( cd "$nb" && echo "$pay2" | python3 "$here_root/hooks/kanon-hook.py" PreToolUse )
[ -z "$nag" ] && echo "ok    PreToolUse silent with an existing stale checklist" \
  || { echo "ERROR PreToolUse requests a checklist that exists"; fail=1; }
command rm -rf "$nb" "${TMPDIR:-/tmp}/kanon-$(id -u)"

# Missing frontmatter fields and empty gathered material each require an error.
fb=$(mktemp -d)
mk () { printf -- '---\ntask: %s\nopened: %s\nclosed: %s\nslots: null\nsource: -\n---\n\n## Gathered\n%s\n\n## Acceptance\n- [x] 1. r · check: c · proof: коммит a1b2c3d\n' "$1" "$2" "$3" "$4"; }
mk ""        2026-09-02 null "- x · y" > "$fb/notask.md"
mk t         неdata     null "- x · y" > "$fb/badopened.md"
mk t         2026-09-02 позавчера "- x · y" > "$fb/badclosed.md"
mk t         2026-09-02 null ""        > "$fb/emptygathered.md"
printf -- '---\ntask: сделай три варианта\nopened: 2026-09-02\nclosed: null\nsource: -\n---\n\n## Gathered\n- x · y\n\n## Acceptance\n- [x] 1. r · check: c · proof: коммит a1b2c3d\n' > "$fb/noslots.md"
for probe in "notask:task field" "badopened:opened date" "badclosed:closed date" \
             "emptygathered:Gathered content" "noslots:slots field"; do
  f=${probe%%:*}; what=${probe#*:}
  python3 scripts/check-checklist.py "$fb/$f.md" >/dev/null 2>&1 \
    && { echo "ERROR linter missed $what"; fail=1; } \
    || echo "ok    linter catches missing $what"
done
command rm -rf "$fb"

# Regression cases from independent review cover linter and sweep outcomes.
cb=$(mktemp -d); mkdir -p "$cb/_kanon"
head_of () { printf -- '---\ntask: %s\nopened: 2026-09-02\nclosed: %s\nslots: %s\nsource: -\n---\n\n## Gathered\n- x · y\n\n## Acceptance\n' "$1" "$2" "$3"; }
{ head_of t null null; printf -- '- [ ] 1. результат без проверки\n'; } > "$cb/nocheck.md"
{ head_of t null null; printf -- '- [x] 1. r · check: c · proof: коммит a1b2c3d\n- [x] 1. дубль · check: c · proof: коммит deadbee\n'; } > "$cb/dup.md"
{ head_of t 2026-99-99 null; printf -- '- [x] 1. r · check: c · proof: коммит a1b2c3d\n'; } > "$cb/baddate.md"
{ head_of "сделай три варианта" null null; printf -- '- [x] 1. r · check: c · proof: коммит a1b2c3d\n'; } > "$cb/qty.md"
{ head_of t null null; printf -- '- [x] 1. r · check: c · proof: коммит a1b2c3d\n\n## Failures\n\n[!] 1\n'; } > "$cb/nofail.md"
{ head_of t null "²"; printf -- '- [x] 1. r · check: c · proof: коммит a1b2c3d\n'; } > "$cb/unislots.md"
for probe in "nocheck:item without check or marker" "dup:duplicate numbers" \
             "baddate:invalid date" "nofail:failure without attempt fields" \
             "unislots:Unicode numeral in slots"; do
  f=${probe%%:*}; what=${probe#*:}
  python3 scripts/check-checklist.py "$cb/$f.md" >/dev/null 2>&1 \
    && { echo "ERROR linter missed $what"; fail=1; } \
    || echo "ok    linter catches $what"
done
python3 scripts/check-checklist.py "$cb/qty.md" 2>&1 | grep -q 'три' \
  && echo "ok    quantity with slots=null produces a warning" \
  || { echo "ERROR no warning about task quantity"; fail=1; }
python3 scripts/check-checklist.py "$cb/unislots.md" 2>&1 | grep -qi 'traceback' \
  && { echo "ERROR Unicode numeral crashes the linter"; fail=1; } \
  || echo "ok    Unicode numeral produces an error without traceback"

# One unreadable file must not hide readable neighbors.
printf '\xff\xfe не utf-8' > "$cb/_kanon/broken.md"
cp tests/fixtures/good-ru.md "$cb/_kanon/live.md"
( cd "$cb" && python3 "$here_root/scripts/check-checklist.py" 2>&1 | grep -q 'live.md' ) \
  && echo "ok    broken checklist does not hide its neighbors" \
  || { echo "ERROR one broken file hid its neighbors"; fail=1; }
st=$( cd "$cb" && echo '{}' | python3 "$here_root/hooks/kanon-hook.py" Stop )
echo "$st" | grep -q 'systemMessage' \
  && echo "ok    hook sees a checklist beside a broken file" \
  || { echo "ERROR hook silent because of one broken file"; fail=1; }

# Checklist symlinks must not expose a file outside the project.
echo "PRIVATE" > "$cb/secret.md"
ln -s "$cb/secret.md" "$cb/_kanon/link.md"
( cd "$cb" && python3 "$here_root/scripts/check-checklist.py" 2>&1 | grep -q 'PRIVATE' ) \
  && { echo "ERROR symlink contents read"; fail=1; } \
  || echo "ok    symlink checklist not read"
( cd "$cb" && python3 "$here_root/scripts/check-checklist.py" 2>&1 | grep -q 'symlink skipped' ) \
  && echo "ok    skipped symlink reported" \
  || { echo "ERROR symlink skipped silently"; fail=1; }

# An empty folder updates an owned index rather than leaving stale entries.
eb=$(mktemp -d); mkdir -p "$eb/_kanon"
printf '# kanon · checklists\n\nстарое\n' > "$eb/_kanon/INDEX.md"
( cd "$eb" && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 )
grep -q 'старое' "$eb/_kanon/INDEX.md" \
  && { echo "ERROR owned index not updated in an empty directory"; fail=1; } \
  || echo "ok    empty directory updates the owned index"

# A directory name does not authorize replacing a foreign INDEX.md.
fo=$(mktemp -d); mkdir -p "$fo/_kanon"; echo "ЧУЖОЙ" > "$fo/_kanon/INDEX.md"
( cd "$fo" && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 ) || true
grep -q 'ЧУЖОЙ' "$fo/_kanon/INDEX.md" \
  && echo "ok    foreign INDEX.md preserved in an empty directory" \
  || { echo "ERROR foreign INDEX.md overwritten"; fail=1; }
cp tests/fixtures/good-ru.md "$fo/_kanon/c.md"
( cd "$fo" && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 ) || true
grep -q 'ЧУЖОЙ' "$fo/_kanon/INDEX.md" \
  && echo "ok    foreign INDEX.md preserved with a checklist" \
  || { echo "ERROR foreign INDEX.md overwritten with a checklist"; fail=1; }

# Replacing an index must not widen its private permissions.
pm=$(mktemp -d); mkdir -p "$pm/_kanon"
cp tests/fixtures/good-ru.md "$pm/_kanon/c.md"
( cd "$pm" && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 )
chmod 600 "$pm/_kanon/INDEX.md"
( cd "$pm" && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 )
[ "$(stat -c %a "$pm/_kanon/INDEX.md")" = "600" ] \
  && echo "ok    index mode preserved on rebuild" \
  || { echo "ERROR index mode broadened to $(stat -c %a "$pm/_kanon/INDEX.md")"; fail=1; }

# chmod must preserve inherited mode bits despite umask.
chmod 666 "$pm/_kanon/INDEX.md"
( cd "$pm" && umask 022 && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 )
[ "$(stat -c %a "$pm/_kanon/INDEX.md")" = "666" ] \
  && echo "ok    umask does not narrow the inherited index mode" \
  || { echo "ERROR mode narrowed to $(stat -c %a "$pm/_kanon/INDEX.md")"; fail=1; }
command rm -rf "$fo" "$pm"

# A sixth open item must be reported rather than silently truncated.
{ head_of "много" null null
  for i in 1 2 3 4 5 6; do printf -- '- [ ] %d. пункт · check: c\n' "$i"; done
} > "$eb/_kanon/many.md"
touch -d "20 days ago" "$eb/_kanon/many.md"
( cd "$eb" && python3 "$here_root/scripts/sweep.py" 2>&1 | grep -q 'and another' ) \
  && echo "ok    open-item truncation reported by count" \
  || { echo "ERROR sixth open item silently lost"; fail=1; }
command rm -rf "$cb" "$eb"

# Additional representation-boundary regressions.
tb=$(mktemp -d); mkdir -p "$tb/_kanon"
hf () { printf -- '---\ntask: t\nopened: 2026-09-02\nclosed: null\nslots: null\nsource: -\n---\n\n## Gathered\n- x · y\n\n## Acceptance\n- [x] 1. r · check: c · proof: коммит a1b2c3d\n\n## Failures\n%s\n' "$1"; }
hf '[!] 1 · tried: x · returned: y' > "$tb/nodate.md"
hf '[!] 1 · returned: y · 2026-09-02' > "$tb/notried.md"
hf '[!] 1 · tried: x · 2026-09-02' > "$tb/noreturned.md"
hf '[!] 1 · tried: x · returned: y · 2026-99-99' > "$tb/baddate.md"
hf '[!] 1 · tried: x · returned: y · 2026-09-02' > "$tb/okdate.md"
python3 scripts/check-checklist.py "$tb/nodate.md" >/dev/null 2>&1 \
  && { echo "ERROR failure without a date accepted"; fail=1; } || echo "ok    failure without a date rejected"
for probe in "notried:without tried" "noreturned:without returned"; do
  f=${probe%%:*}; what=${probe#*:}
  python3 scripts/check-checklist.py "$tb/$f.md" >/dev/null 2>&1 \
    && { echo "ERROR failure $what accepted"; fail=1; } \
    || echo "ok    failure $what rejected"
done
python3 scripts/check-checklist.py "$tb/baddate.md" >/dev/null 2>&1 \
  && { echo "ERROR failure with invalid date accepted"; fail=1; } || echo "ok    failure date validated against the calendar"
python3 scripts/check-checklist.py "$tb/okdate.md" >/dev/null 2>&1 \
  && echo "ok    valid failure accepted" || { echo "ERROR valid failure rejected:"; python3 scripts/check-checklist.py "$tb/okdate.md"; fail=1; }

# Oversized item numbers must not hide other checklists.
big=$(python3 -c "print('9'*5000)")
printf -- '---\ntask: t\nopened: 2026-09-02\nclosed: null\nslots: null\nsource: -\n---\n\n## Gathered\n- x · y\n\n## Acceptance\n- [ ] %s. r · check: c\n' "$big" > "$tb/_kanon/huge.md"
cp tests/fixtures/good-ru.md "$tb/_kanon/live.md"
( cd "$tb" && python3 "$here_root/scripts/check-checklist.py" 2>&1 | grep -q 'live.md' ) \
  && echo "ok    huge number does not hide a neighboring checklist" \
  || { echo "ERROR huge number broke directory parsing"; fail=1; }
( cd "$tb" && python3 "$here_root/scripts/check-checklist.py" 2>&1 | grep -qi 'traceback' ) \
  && { echo "ERROR traceback on a huge number"; fail=1; } || echo "ok    huge number handled without traceback"
# Oversized numbers are malformed input, not an unreadable-file traceback.
( cd "$tb" && python3 "$here_root/scripts/check-checklist.py" 2>&1 | grep -q 'not parsed' ) \
  && echo "ok    huge number reported as a format defect" \
  || { echo "ERROR huge number not reported as a format defect"; fail=1; }

# Bash gathering and writing must reach the sensors in shell-based workflows.
bb=$(mktemp -d); tr4="$bb/tr.jsonl"
for c in 'cat src/a.py' 'sed -n 1,40p src/b.py' 'git log --oneline -5' 'grep -rn foo src'; do
  printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"%s"}}]}}\n' "$c"
done > "$tr4"
bsay () { printf '{"session_id":"%s","transcript_path":"%s","tool_name":"Bash","tool_input":{"command":"%s"}}' "$1" "$tr4" "$2" \
  | ( cd "$bb" && python3 "$here_root/hooks/kanon-hook.py" PreToolUse ); }
w=$(bsay "bash-w-$$" "cat > $bb/src/a.py <<EOF")
[ -n "$w" ] && echo "ok    Bash gathering and heredoc writes recognized" \
  || { echo "ERROR hook missed Bash gathering and writing"; fail=1; }
r=$(bsay "bash-r-$$" "ls -la $bb/src")
[ -z "$r" ] && echo "ok    reading Bash command is not production" \
  || { echo "ERROR hook reminded on ls"; fail=1; }
k=$(bsay "bash-k-$$" "cat > $bb/_kanon/2026-09-03-x.md <<EOF")
[ -z "$k" ] && echo "ok    Bash checklist write is not production" \
  || { echo "ERROR hook requests a checklist during checklist writing"; fail=1; }
n=$(bsay "bash-n-$$" "python3 t.py >/dev/null 2>&1")
[ -z "$n" ] && echo "ok    /dev/null redirection is not a write" \
  || { echo "ERROR /dev/null treated as a write"; fail=1; }
# Writing commands in a transcript must not count toward the gathering threshold.
tr5="$bb/tr5.jsonl"
for c in 'sed -i s/a/b/ x.py' 'cat > y.py <<EOF' 'ls'; do
  printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"%s"}}]}}\n' "$c"
done > "$tr5"
m=$(printf '{"session_id":"bash-m-%s","transcript_path":"%s","tool_name":"Bash","tool_input":{"command":"cat > z.py <<EOF"}}' "$$" "$tr5" \
  | ( cd "$bb" && python3 "$here_root/hooks/kanon-hook.py" PreToolUse ))
[ -z "$m" ] && echo "ok    writing Bash commands are not gathering" \
  || { echo "ERROR sed -i counted as gathering"; fail=1; }
command rm -rf "$bb"

# Count Bash gathering without a usable Codex transcript; recognize apply_patch.
cb2=$(mktemp -d); mkdir -p "$cb2/src"
csay () { printf '{"session_id":"%s","transcript_path":null,"tool_name":"%s","tool_input":{"command":"%s"}}' "$1" "$2" "$3" \
  | ( cd "$cb2" && python3 "$here_root/hooks/kanon-hook.py" PreToolUse ); }
cs="codex-$$"
early=$(csay "$cs" Bash "cat src/a.py"); csay "$cs" Bash "sed -n 1,9p src/b.py" >/dev/null
[ -z "$early" ] && echo "ok    two reads without transcript remain silent" \
  || { echo "ERROR reminder before threshold without transcript"; fail=1; }
csay "$cs" Bash "git log --oneline -3" >/dev/null
cw=$(csay "$cs" apply_patch "*** Begin Patch\n*** Add File: src/c.txt\n+hello\n*** End Patch")
[ -n "$cw" ] && echo "ok    Codex: three Bash reads and apply_patch trigger a reminder without transcript" \
  || { echo "ERROR Codex path: gathering undercounted or apply_patch missed"; fail=1; }
cs2="codex-k-$$"
for i in 1 2 3; do csay "$cs2" Bash "cat src/a.py" >/dev/null; done
ck=$(csay "$cs2" apply_patch "*** Begin Patch\n*** Add File: _kanon/2026-09-03-x.md\n+---\n*** End Patch")
[ -z "$ck" ] && echo "ok    apply_patch in _kanon/ is a checklist write" \
  || { echo "ERROR apply_patch in _kanon/ treated as production"; fail=1; }
command rm -rf "$cb2" "${TMPDIR:-/tmp}/kanon-$(id -u)"

# Distinct session IDs must not share a reminder marker.
mk=$(mktemp -d); tr3="$mk/tr.jsonl"
for i in 1 2 3 4; do echo '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read"}]}}'; done > "$tr3"
say () { echo "{\"session_id\":\"$1\",\"transcript_path\":\"$tr3\",\"tool_input\":{\"file_path\":\"$mk/src/a.py\"}}" \
  | ( cd "$mk" && python3 "$here_root/hooks/kanon-hook.py" PreToolUse ); }
a=$(say "collide-a/b"); b=$(say "collide-ab")
[ -n "$a" ] && [ -n "$b" ] \
  && echo "ok    similar session IDs do not share a marker" \
  || { echo "ERROR second session lost its reminder"; fail=1; }
command rm -rf "$tb" "$mk" "${TMPDIR:-/tmp}/kanon-$(id -u)"

# Cover current/legacy/configured directory names and exclude the derived index.
tmp=$(mktemp -d)
mkdir -p "$tmp/_kanon" "$tmp/legacy/.kanon" "$tmp/env/custom"
# Use a malformed fixture: a valid fixture could pass when discovery is entirely disabled.
cp tests/fixtures/bad-ru.md "$tmp/_kanon/x.md"
cp tests/fixtures/bad-ru.md "$tmp/legacy/.kanon/x.md"
cp tests/fixtures/bad-ru.md "$tmp/env/custom/x.md"
cp tests/fixtures/good-ru.md "$tmp/_kanon/ok.md"
here=$(pwd)
( cd "$tmp" && python3 "$here/scripts/check-checklist.py" 2>&1 | grep -q 'empty claim' ) \
  && echo "ok    _kanon directory found" || { echo "ERROR _kanon not found"; fail=1; }
( cd "$tmp/legacy" && python3 "$here/scripts/check-checklist.py" 2>&1 | grep -q 'empty claim' ) \
  && echo "ok    legacy .kanon accepted" || { echo "ERROR .kanon not accepted"; fail=1; }
( cd "$tmp/env" && KANON_DIR=custom python3 "$here/scripts/check-checklist.py" 2>&1 | grep -q 'empty claim' ) \
  && echo "ok    KANON_DIR overrides discovery" || { echo "ERROR KANON_DIR"; fail=1; }
( cd "$tmp" && python3 "$here/scripts/sweep.py" >/dev/null 2>&1 )
[ -f "$tmp/_kanon/INDEX.md" ] && echo "ok    INDEX.md generated" \
  || { echo "ERROR INDEX.md not generated"; fail=1; }
if ( cd "$tmp" && python3 "$here/scripts/check-checklist.py" 2>&1 | grep -q INDEX ); then
  echo "ERROR INDEX.md treated as a checklist"; fail=1
else
  echo "ok    INDEX.md excluded from checklists"
fi
command rm -rf "$tmp"

exit $fail
