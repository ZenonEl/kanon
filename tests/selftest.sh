#!/usr/bin/env bash
# Самопроверка линтера: он обязан пропускать корректные чеклисты на обоих
# языках и отказывать на дефектном. Тест на мутацию: снимаешь защиту — краснеет.
set -u
cd "$(dirname "$0")/.."
fail=0

for f in tests/fixtures/good-en.md tests/fixtures/good-ru.md; do
  if python3 scripts/check-checklist.py "$f" >/dev/null 2>&1; then
    echo "ok    $f принят"
  else
    echo "ОШИБКА $f должен приниматься:"; python3 scripts/check-checklist.py "$f"; fail=1
  fi
done

out=$(python3 scripts/check-checklist.py tests/fixtures/bad-ru.md 2>&1)
if [ $? -eq 0 ]; then
  echo "ОШИБКА bad-ru.md должен отвергаться"; fail=1
else
  for expect in "пустое утверждение" "несуществующий пункт" "slots=3"; do
    if echo "$out" | grep -q "$expect"; then
      echo "ok    поймано: $expect"
    else
      echo "ОШИБКА не поймано: $expect"; echo "$out"; fail=1
    fi
  done
fi

python3 scripts/sweep.py >/dev/null 2>&1 \
  && echo "ok    sweep не падает без каталога" \
  || { echo "ОШИБКА sweep упал без каталога"; fail=1; }

# Устойчивость: хук обязан молчать и не падать на кривом входе.
for e in SessionStart PreToolUse Stop; do
  echo '{}' | python3 hooks/kanon-hook.py "$e" >/dev/null 2>&1 \
    && echo "ok    хук $e не падает на пустом входе" \
    || { echo "ОШИБКА хук $e упал"; fail=1; }
done
echo 'мусор' | python3 hooks/kanon-hook.py PreToolUse >/dev/null 2>&1 \
  && echo "ok    хук не падает на мусоре" || { echo "ОШИБКА хук упал на мусоре"; fail=1; }

# Содержательность: код возврата у хука ВСЕГДА 0 по требованию проекта, поэтому
# проверять надо вывод. Без этого тесты зелены при полностью мёртвых хуках.
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
echo "$out" | grep -q '7\.'   && echo "ok    Stop называет незакрытый пункт"   || { echo "ОШИБКА Stop молчит при открытом пункте"; fail=1; }

# PreToolUse: сбор был, чеклиста нет — обязан сказать, и ровно один раз.
pb=$(mktemp -d); tr="$pb/tr.jsonl"
for i in 1 2 3 4; do echo '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read"}]}}'; done > "$tr"
sid="selftest-$$"
pay="{\"session_id\":\"$sid\",\"transcript_path\":\"$tr\",\"tool_input\":{\"file_path\":\"$pb/src/a.py\"}}"
first=$( cd "$pb" && echo "$pay" | python3 "$here/hooks/kanon-hook.py" PreToolUse )
second=$( cd "$pb" && echo "$pay" | python3 "$here/hooks/kanon-hook.py" PreToolUse )
[ -n "$first" ] && echo "ok    PreToolUse напоминает при сборе без чеклиста"   || { echo "ОШИБКА PreToolUse смолчал, хотя сбор был"; fail=1; }
[ -z "$second" ] && echo "ok    PreToolUse говорит один раз за сессию"   || { echo "ОШИБКА PreToolUse повторился в той же сессии"; fail=1; }
command rm -rf "$hb" "$pb" "/tmp/kanon-reminded-$sid"

# Пункт, который не разобрался, обязан быть ошибкой, а не тишиной.
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
if python3 scripts/check-checklist.py "$mb/malformed.md" 2>&1 | grep -q 'не разобрано'; then
  echo "ok    нераспознанный пункт — ошибка, не тишина"
else
  echo "ОШИБКА нераспознанный пункт проглочен"; fail=1
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
  echo "ok    двуязычный заголовок раздела распознан"
else
  echo "ОШИБКА двуязычный заголовок не распознан:"
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
  && { echo "ОШИБКА чеклист без приёмки принят"; fail=1; } \
  || echo "ok    чеклист без раздела приёмки отвергнут"

# Доказательство-путь и доказательство с точкой внутри обязаны приниматься.
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
  && echo "ok    путь и доказательство с точкой приняты" \
  || { echo "ОШИБКА валидное доказательство отвергнуто:"; python3 scripts/check-checklist.py "$mb/proofs.md"; fail=1; }
command rm -rf "$mb"

# Каталог: новое имя, историческое, переопределение, INDEX не чеклист.
tmp=$(mktemp -d)
mkdir -p "$tmp/_kanon" "$tmp/legacy/.kanon" "$tmp/env/custom"
cp tests/fixtures/good-ru.md "$tmp/_kanon/x.md"
cp tests/fixtures/good-ru.md "$tmp/legacy/.kanon/x.md"
cp tests/fixtures/good-ru.md "$tmp/env/custom/x.md"
here=$(pwd)
( cd "$tmp" && python3 "$here/scripts/check-checklist.py" >/dev/null 2>&1 ) \
  && echo "ok    каталог _kanon найден" || { echo "ОШИБКА _kanon не найден"; fail=1; }
( cd "$tmp/legacy" && python3 "$here/scripts/check-checklist.py" >/dev/null 2>&1 ) \
  && echo "ok    историческое .kanon принимается" || { echo "ОШИБКА .kanon не принят"; fail=1; }
( cd "$tmp/env" && KANON_DIR=custom python3 "$here/scripts/check-checklist.py" >/dev/null 2>&1 ) \
  && echo "ok    KANON_DIR переопределяет" || { echo "ОШИБКА KANON_DIR"; fail=1; }
( cd "$tmp" && python3 "$here/scripts/sweep.py" >/dev/null 2>&1 )
[ -f "$tmp/_kanon/INDEX.md" ] && echo "ok    INDEX.md собран" \
  || { echo "ОШИБКА INDEX.md не собран"; fail=1; }
if ( cd "$tmp" && python3 "$here/scripts/check-checklist.py" 2>&1 | grep -q INDEX ); then
  echo "ОШИБКА INDEX.md попал в чеклисты"; fail=1
else
  echo "ok    INDEX.md чеклистом не считается"
fi
command rm -rf "$tmp"

exit $fail
