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

exit $fail
