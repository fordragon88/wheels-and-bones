#!/usr/bin/env bash
# Перевод частей chunk5 бесплатной моделью opencode (параллельно). Результат: i18n_work/oc/out<i>.txt
D="$HOME/.claude/skills/opencode-delegate"
cd /d/wheels_and_bones/i18n_work/oc
M=${1:-opencode/deepseek-v4.1-flash-free}
for i in 0 1 2 3 4 5 6 7; do
  bash $D/delegate.sh -m "$M" -t 600 -f ../GUIDE.md -f part$i.json \
    "Translate the game UI strings in the attached part$i.json from Russian to English following the attached GUIDE.md exactly (names, glossary, rules, placeholders {0} {1}, ALL-CAPS stays ALL-CAPS, «» -> “”). The 'context' field is only the source line for context. NEW names in this batch: Кицунэ Юки -> Yuki the kitsune; Дриада Ивушка -> Ivushka the dryad; Дракончик Искра -> Iskra the little dragon; Бабушка Агата -> Granny Agatha (owl); Ящерка-картограф Сайра -> Saira the lizardfolk cartographer; Барсучиха-пасечница Матильда -> Matilda the badger beekeeper. Seating terms: посадка/позиционирование -> seating/positioning; сидение на крестце -> sacral sitting (posterior pelvic tilt); наклон сиденья (tilt) -> tilt-in-space; откидывание спинки -> recline; седалищные бугры -> ischial tuberosities (sitting bones); подножка -> footrest; карта терапевта -> therapist's card; антиопрокидыватель -> anti-tipper; трос наклона -> tilt cable; курок наклона -> tilt trigger. Output ONLY one JSON object {\"<russian string exactly as given>\": \"<english>\"} with every item, nothing else, no code fences." > out$i.txt 2>&1 &
done
wait
echo done
