#!/usr/bin/env bash
# Самопроверка линтера: он обязан пропускать корректные чеклисты на обоих
# языках и отказывать на дефектном. Тест на мутацию: снимаешь защиту — краснеет.
set -u
cd "$(dirname "$0")/.."
here_root=$(pwd)
fail=0

# Разбор против спеки. Отдельным файлом, потому что здесь проверяются значения,
# а не коды возврата: пять правок держались проверками, смотревшими только rc.
python3 tests/test_parser.py || fail=1

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
# Форма вывода, а не только его наличие. Голый stdout у Stop и PreToolUse хост
# отправляет в отладочный лог: показывает он его только у SessionStart,
# UserPromptSubmit и UserPromptExpansion. Текст, не доехавший до адресата,
# неотличим от отсутствующего сенсора.
if echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); assert isinstance(d.get('systemMessage'),str) and d['systemMessage']; assert 'decision' not in d" 2>/dev/null; then
  echo "ok    Stop отдаёт JSON с systemMessage и не блокирует"
else
  echo "ОШИБКА Stop печатает не JSON — вывод не доедет до адресата"; fail=1
fi
# У SessionStart вывод появляется только при заброшенном или истёкшем: без него
# ассерт формы проверял бы пустую строку, то есть ничего.
cp "$hb/_kanon/h.md" "$hb/_kanon/stale.md"; touch -d "30 days ago" "$hb/_kanon/stale.md"
ss=$( cd "$hb" && echo '{}' | python3 "$here/hooks/kanon-hook.py" SessionStart )
[ -n "$ss" ] && echo "ok    SessionStart говорит про заброшенное" \
  || { echo "ОШИБКА SessionStart молчит при заброшенном чеклисте"; fail=1; }
case "$ss" in
  "{"*) echo "ОШИБКА SessionStart печатает JSON, хотя stdout у него доходит"; fail=1 ;;
  *)    echo "ok    SessionStart печатает обычный текст" ;;
esac

# PreToolUse: сбор был, чеклиста нет — обязан сказать, и ровно один раз.
pb=$(mktemp -d); tr="$pb/tr.jsonl"
for i in 1 2 3 4; do echo '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read"}]}}'; done > "$tr"
sid="selftest-$$"
pay="{\"session_id\":\"$sid\",\"transcript_path\":\"$tr\",\"tool_input\":{\"file_path\":\"$pb/src/a.py\"}}"
first=$( cd "$pb" && echo "$pay" | python3 "$here/hooks/kanon-hook.py" PreToolUse )
second=$( cd "$pb" && echo "$pay" | python3 "$here/hooks/kanon-hook.py" PreToolUse )
[ -n "$first" ] && echo "ok    PreToolUse напоминает при сборе без чеклиста"   || { echo "ОШИБКА PreToolUse смолчал, хотя сбор был"; fail=1; }
if echo "$first" | python3 -c "import json,sys; d=json.load(sys.stdin); assert isinstance(d.get('systemMessage'),str) and d['systemMessage']; assert 'permissionDecision' not in str(d)" 2>/dev/null; then
  echo "ok    PreToolUse отдаёт JSON с systemMessage и не трогает разрешения"
else
  echo "ОШИБКА PreToolUse печатает не JSON — вывод не доедет до адресата"; fail=1
fi
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

# Раздел есть, но пуст — отдельный случай: он проходил, пока проверялось только
# отсутствие раздела.
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
  && { echo "ОШИБКА пустой раздел приёмки принят"; fail=1; } \
  || echo "ok    пустой раздел приёмки отвергнут"

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

# Ошибка обязана давать код возврата 1, даже если её текст содержит «(!)»:
# в текст подставляется пользовательский ввод, а rc смотрит CI.
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
  && { echo "ОШИБКА пункт с (!) дал код 0 при напечатанной ошибке"; fail=1; } \
  || echo "ok    ошибка с «(!)» в тексте даёт код возврата 1"
command rm -rf "$sb"

# sweep обязан напечатать отчёт, даже если INDEX.md не записывается.
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
echo "$out" | grep -q 'STALE\|ЗАБРОШЕН' \
  && echo "ok    sweep печатает отчёт при незаписываемом INDEX.md" \
  || { echo "ОШИБКА sweep потерял отчёт:"; echo "$out"; fail=1; }
command rm -rf "$wb"

# INDEX.md пишется автоматически из хука в любом каталоге, куда зашла сессия.
# Симлинк на его месте уводил запись в произвольный файл — проверяем отказ.
lb=$(mktemp -d); mkdir -p "$lb/_kanon"
echo "не трогать" > "$lb/victim.txt"
ln -s "$lb/victim.txt" "$lb/_kanon/INDEX.md"
cp tests/fixtures/good-ru.md "$lb/_kanon/c.md"
( cd "$lb" && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 ) || true
if [ "$(cat "$lb/victim.txt")" = "не трогать" ]; then
  echo "ok    запись INDEX.md не идёт по симлинку"
else
  echo "ОШИБКА sweep перезаписал файл по симлинку"; fail=1
fi

# Жёсткая ссылка — второе имя того же inode, и O_NOFOLLOW её не видит: запись
# должна идти через подмену имени, иначе усечение доходит до жертвы.
hl=$(mktemp -d); mkdir -p "$hl/_kanon"
echo "не трогать" > "$hl/victim.txt"
ln "$hl/victim.txt" "$hl/_kanon/INDEX.md"
cp tests/fixtures/good-ru.md "$hl/_kanon/c.md"
( cd "$hl" && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 ) || true
if [ "$(cat "$hl/victim.txt")" = "не трогать" ]; then
  echo "ok    запись INDEX.md не идёт по жёсткой ссылке"
else
  echo "ОШИБКА sweep перезаписал файл по жёсткой ссылке"; fail=1
fi
ls "$hl/_kanon"/.INDEX.md.tmp-* >/dev/null 2>&1 \
  && { echo "ОШИБКА временный файл индекса не убран"; fail=1; } \
  || echo "ok    временный файл индекса не остаётся"
# Путь очистки: подмена падает, временный файл не должен остаться мусором.
dl=$(mktemp -d); mkdir -p "$dl/_kanon/INDEX.md"
cp tests/fixtures/good-ru.md "$dl/_kanon/c.md"
out_dir=$( cd "$dl" && python3 "$here_root/scripts/sweep.py" 2>&1 || true )
echo "$out_dir" | grep -q 'в работе' \
  && echo "ok    отчёт печатается, когда индекс не записать" \
  || { echo "ОШИБКА отчёт потерян при непишущемся индексе"; fail=1; }
if ls "$dl/_kanon"/.INDEX.md.tmp-* >/dev/null 2>&1; then
  echo "ОШИБКА временный файл остался после неудачной подмены"; fail=1
else
  echo "ok    временный файл убран после неудачной подмены"
fi
command rm -rf "$dl"

command rm -rf "$hl"
out_sym=$( cd "$lb" && python3 "$here_root/scripts/sweep.py" 2>&1 || true )
echo "$out_sym" | grep -q 'в работе\|STALE\|ЗАБРОШЕН' \
  && echo "ok    отчёт печатается и при отказе записи индекса" \
  || { echo "ОШИБКА отчёт потерян при симлинке"; fail=1; }
command rm -rf "$lb"

# PreToolUse не должен требовать новый чеклист при живом заброшенном.
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
[ -z "$nag" ] && echo "ok    PreToolUse молчит при живом заброшенном чеклисте" \
  || { echo "ОШИБКА PreToolUse требует чеклист, хотя он есть"; fail=1; }
command rm -rf "$nb" "/tmp/kanon-reminded-$sid2"

# Обязательные поля frontmatter и пустой Gathered: каждая проверка линтера
# должна иметь свой ассерт, иначе её снятие проходит молча.
fb=$(mktemp -d)
mk () { printf -- '---\ntask: %s\nopened: %s\nclosed: %s\nslots: null\nsource: -\n---\n\n## Gathered\n%s\n\n## Acceptance\n- [x] 1. r · check: c · proof: коммит a1b2c3d\n' "$1" "$2" "$3" "$4"; }
mk ""        2026-09-02 null "- x · y" > "$fb/notask.md"
mk t         неdata     null "- x · y" > "$fb/badopened.md"
mk t         2026-09-02 позавчера "- x · y" > "$fb/badclosed.md"
mk t         2026-09-02 null ""        > "$fb/emptygathered.md"
printf -- '---\ntask: сделай три варианта\nopened: 2026-09-02\nclosed: null\nsource: -\n---\n\n## Gathered\n- x · y\n\n## Acceptance\n- [x] 1. r · check: c · proof: коммит a1b2c3d\n' > "$fb/noslots.md"
for probe in "notask:поля task" "badopened:даты opened" "badclosed:даты closed" \
             "emptygathered:пустого Gathered" "noslots:пропущенного slots"; do
  f=${probe%%:*}; what=${probe#*:}
  python3 scripts/check-checklist.py "$fb/$f.md" >/dev/null 2>&1 \
    && { echo "ОШИБКА линтер не заметил $what"; fail=1; } \
    || echo "ok    линтер ловит отсутствие $what"
done
command rm -rf "$fb"

# Находки Codex, проверяемые через линтер и sweep.
cb=$(mktemp -d); mkdir -p "$cb/_kanon"
head_of () { printf -- '---\ntask: %s\nopened: 2026-09-02\nclosed: %s\nslots: %s\nsource: -\n---\n\n## Gathered\n- x · y\n\n## Acceptance\n' "$1" "$2" "$3"; }
{ head_of t null null; printf -- '- [ ] 1. результат без проверки\n'; } > "$cb/nocheck.md"
{ head_of t null null; printf -- '- [x] 1. r · check: c · proof: коммит a1b2c3d\n- [x] 1. дубль · check: c · proof: коммит deadbee\n'; } > "$cb/dup.md"
{ head_of t 2026-99-99 null; printf -- '- [x] 1. r · check: c · proof: коммит a1b2c3d\n'; } > "$cb/baddate.md"
{ head_of "сделай три варианта" null null; printf -- '- [x] 1. r · check: c · proof: коммит a1b2c3d\n'; } > "$cb/qty.md"
{ head_of t null null; printf -- '- [x] 1. r · check: c · proof: коммит a1b2c3d\n\n## Failures\n\n[!] 1\n'; } > "$cb/nofail.md"
{ head_of t null "²"; printf -- '- [x] 1. r · check: c · proof: коммит a1b2c3d\n'; } > "$cb/unislots.md"
for probe in "nocheck:пункт без check и без пометки" "dup:повтор номеров" \
             "baddate:несуществующую дату" "nofail:провал без полей попытки" \
             "unislots:юникод-цифру в slots"; do
  f=${probe%%:*}; what=${probe#*:}
  python3 scripts/check-checklist.py "$cb/$f.md" >/dev/null 2>&1 \
    && { echo "ОШИБКА линтер пропустил $what"; fail=1; } \
    || echo "ok    линтер ловит $what"
done
python3 scripts/check-checklist.py "$cb/qty.md" 2>&1 | grep -q 'три' \
  && echo "ok    количество в задаче при slots=null — предупреждение" \
  || { echo "ОШИБКА не предупредил про количество в задаче"; fail=1; }
python3 scripts/check-checklist.py "$cb/unislots.md" 2>&1 | grep -qi 'traceback' \
  && { echo "ОШИБКА юникод-цифра роняет линтер трейсбеком"; fail=1; } \
  || echo "ok    юникод-цифра даёт ошибку, а не трейсбек"

# Битый файл не должен ослеплять остальные.
printf '\xff\xfe не utf-8' > "$cb/_kanon/broken.md"
cp tests/fixtures/good-ru.md "$cb/_kanon/live.md"
( cd "$cb" && python3 "$here_root/scripts/check-checklist.py" 2>&1 | grep -q 'live.md' ) \
  && echo "ok    битый чеклист не ослепляет соседние" \
  || { echo "ОШИБКА один битый файл скрыл остальные"; fail=1; }
st=$( cd "$cb" && echo '{}' | python3 "$here_root/hooks/kanon-hook.py" Stop )
echo "$st" | grep -q 'systemMessage' \
  && echo "ok    хук видит живой чеклист рядом с битым" \
  || { echo "ОШИБКА хук онемел из-за одного битого файла"; fail=1; }

# Симлинк-чеклист не читается: он мог бы выдать файл вне проекта.
echo "PRIVATE" > "$cb/secret.md"
ln -s "$cb/secret.md" "$cb/_kanon/link.md"
( cd "$cb" && python3 "$here_root/scripts/check-checklist.py" 2>&1 | grep -q 'PRIVATE' ) \
  && { echo "ОШИБКА содержимое по симлинку прочитано"; fail=1; } \
  || echo "ok    чеклист по симлинку не читается"
( cd "$cb" && python3 "$here_root/scripts/check-checklist.py" 2>&1 | grep -q 'симлинк пропущен' ) \
  && echo "ok    пропуск симлинка показан, а не молчаливый" \
  || { echo "ОШИБКА симлинк пропущен молча"; fail=1; }

# Опустевший каталог обязан обновить индекс, а не оставить старый.
eb=$(mktemp -d); mkdir -p "$eb/_kanon"; echo "старое" > "$eb/_kanon/INDEX.md"
( cd "$eb" && python3 "$here_root/scripts/sweep.py" >/dev/null 2>&1 )
grep -q 'старое' "$eb/_kanon/INDEX.md" \
  && { echo "ОШИБКА индекс не обновлён на пустом каталоге"; fail=1; } \
  || echo "ok    пустой каталог обновляет индекс"

# Заброшенный с шестью открытыми: шестой не должен пропасть молча.
{ head_of "много" null null
  for i in 1 2 3 4 5 6; do printf -- '- [ ] %d. пункт · check: c\n' "$i"; done
} > "$eb/_kanon/many.md"
touch -d "20 days ago" "$eb/_kanon/many.md"
( cd "$eb" && python3 "$here_root/scripts/sweep.py" 2>&1 | grep -q 'и ещё' ) \
  && echo "ok    усечение списка открытых показано счётчиком" \
  || { echo "ОШИБКА шестой открытый пункт пропал молча"; fail=1; }
command rm -rf "$cb" "$eb"

# Каталог: новое имя, историческое, переопределение, INDEX не чеклист.
tmp=$(mktemp -d)
mkdir -p "$tmp/_kanon" "$tmp/legacy/.kanon" "$tmp/env/custom"
# Дефектная фикстура намеренно: на валидной тест зелёный и когда каталог найден,
# и когда обнаружение сломано вовсе — «чеклистов нет» тоже даёт код 0.
cp tests/fixtures/bad-ru.md "$tmp/_kanon/x.md"
cp tests/fixtures/bad-ru.md "$tmp/legacy/.kanon/x.md"
cp tests/fixtures/bad-ru.md "$tmp/env/custom/x.md"
cp tests/fixtures/good-ru.md "$tmp/_kanon/ok.md"
here=$(pwd)
( cd "$tmp" && python3 "$here/scripts/check-checklist.py" 2>&1 | grep -q 'пустое утверждение' ) \
  && echo "ok    каталог _kanon найден" || { echo "ОШИБКА _kanon не найден"; fail=1; }
( cd "$tmp/legacy" && python3 "$here/scripts/check-checklist.py" 2>&1 | grep -q 'пустое утверждение' ) \
  && echo "ok    историческое .kanon принимается" || { echo "ОШИБКА .kanon не принят"; fail=1; }
( cd "$tmp/env" && KANON_DIR=custom python3 "$here/scripts/check-checklist.py" 2>&1 | grep -q 'пустое утверждение' ) \
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
