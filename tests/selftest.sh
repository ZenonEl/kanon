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

python3 scripts/sweep.py >/dev/null 2>&1 && echo "ok    sweep не падает без .kanon/"
for e in SessionStart PreToolUse Stop; do
  echo '{}' | python3 hooks/kanon-hook.py "$e" >/dev/null 2>&1 \
    && echo "ok    хук $e не падает на пустом входе" \
    || { echo "ОШИБКА хук $e упал"; fail=1; }
done
echo 'мусор' | python3 hooks/kanon-hook.py PreToolUse >/dev/null 2>&1 \
  && echo "ok    хук не падает на мусоре" || { echo "ОШИБКА хук упал на мусоре"; fail=1; }

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
