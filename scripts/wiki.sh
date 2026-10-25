#!/bin/sh
# The user guide wiki (wiki/ → the GitHub wiki), kept in step with CHANGELOG.md.
#   scripts/wiki.sh [status]        what the wiki doesn't cover yet, with the pages to update; broken links. Exit 1 when out of date.
#   scripts/wiki.sh mark            after updating the pages: record every changelog line as covered, refresh the footer.
#   scripts/wiki.sh publish [--dry-run]   copy wiki/*.md to the GitHub wiki and push (the wiki needs its first page made on GitHub once).
# A changelog line counts as covered once `mark` has seen it (wiki/.covered-changes); a reworded line shows again.
# Each page's first line `<!-- tracks: a, b -->` lists the words that point a changelog line to it.
cd "$(dirname "$0")/.."
W=wiki; COV="$W/.covered-changes"; CL=CHANGELOG.md
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# Changelog bullets below the header's first --- line, as "heading<TAB>line"
bullets() { awk 'f && /^## /{h=substr($0,4)} f && /^- /{print h "\t" $0} /^---$/{f=1}' "$CL"; }

status() {
  bad=0
  [ -f "$COV" ] && grep -v '^#' "$COV" > "$TMP/seen" || : > "$TMP/seen"
  bullets | awk -F'\t' 'FILENAME == ARGV[1] {seen[$0]=1; next} !($2 in seen)' "$TMP/seen" - > "$TMP/new"
  for p in "$W"/*.md; do sed -n '1s/^<!-- tracks: \(.*\) -->$/\1/p' "$p" | tr ',' '\n' | sed 's/^ *//; s/ *$//' | awk -v pg="$(basename "$p" .md)" 'length{print pg "\t" tolower($0)}'; done > "$TMP/tracks"
  if [ -s "$TMP/new" ]; then
    bad=1; echo "Changelog lines the wiki doesn't cover yet ($(wc -l < "$TMP/new" | tr -d ' ')):"
    awk -F'\t' '
      function word(s, w,   i, r, a, b) { r = s; while ((i = index(r, w)) > 0) { a = (i == 1) ? "" : substr(r, i - 1, 1); b = substr(r, i + length(w), 1); if (a !~ /[a-z0-9]/ && (b == "" || b == "s" || b !~ /[a-z0-9]/)) return 1; r = substr(r, i + 1) } return 0 }
      FILENAME == ARGV[1] { kw[FNR] = $2; pg[FNR] = $1; n = FNR; next }
      $1 != last { print "\n  " $1; last = $1 }
      { l = tolower($2); hit = ""; split("", got); for (k = 1; k <= n; k++) if (!(pg[k] in got) && word(l, kw[k])) { got[pg[k]] = 1; hit = hit (hit ? ", " : "") pg[k] }
        print "  " $2; print "      → " (hit ? hit : "no page matched: pick one, or add a page (and a tracks word)") }' "$TMP/tracks" "$TMP/new"
    echo
  else echo "Every changelog line is covered."; fi
  since=$(sed -n 's/^# commit \([0-9a-f]*\).*/\1/p' "$COV" 2>/dev/null)
  if [ -n "$since" ] && git cat-file -e "$since" 2>/dev/null; then
    log=$(git log --oneline "$since"..HEAD -- "EVE Industry Management.html" CHANGELOG.md docs/FEATURES.md)
    [ -n "$log" ] && { echo "Commits to the app since the wiki was last marked ($since):"; echo "$log" | sed 's/^/  /'; }
    git diff --quiet HEAD -- "EVE Industry Management.html" CHANGELOG.md docs/FEATURES.md 2>/dev/null || echo "Uncommitted changes to the app or its docs: check their changelog lines are in."
  fi
  # Links between pages: [text](Page) or [text](Page#anchor) must name a page in wiki/
  grep -o '](\([A-Za-z0-9_-]*\)\(#[^)]*\)\{0,1\})' "$W"/*.md | sed 's/^\(.*\):](\([^#)]*\).*/\1 \2/' | while read -r f t; do [ -n "$t" ] && [ ! -f "$W/$t.md" ] && echo "Broken link in $f: $t"; done > "$TMP/links"
  for p in "$W"/*.md; do b=$(basename "$p" .md); case "$b" in _*|Home) continue;; esac; grep -q "($b)" "$W/_Sidebar.md" || echo "Not in the sidebar: $b"; done >> "$TMP/links"
  [ -s "$TMP/links" ] && { bad=1; cat "$TMP/links"; }
  [ "$bad" = 0 ] && echo "The wiki is up to date."
  return $bad
}

mark() {
  head=$(git rev-parse --short HEAD); today=$(date +%Y-%m-%d)
  { echo "# commit $head $today (lines below are covered by the wiki; written by scripts/wiki.sh mark)"; bullets | cut -f2-; } > "$COV"
  newest=$(awk '/^---$/{f=1} f && /^## /{print substr($0,4); exit}' "$CL")
  printf '%s\n' "This guide matches the tool as of $today (changelog: *$newest*) · [What changed](https://github.com/GwenRB/EvE-All-in-one-Web-app/blob/main/CHANGELOG.md)" > "$W/_Footer.md"
  echo "Marked $(bullets | wc -l | tr -d ' ') changelog lines as covered (commit $head, $today)."
}

publish() {
  status >/dev/null || echo "Warning: the wiki isn't up to date (run scripts/wiki.sh to see what's missing)."
  url=$(git remote get-url origin | sed 's/\.git$//').wiki.git
  if ! git clone -q "$url" "$TMP/wiki" 2>/dev/null; then
    echo "Couldn't read $url."; echo "Turn the wiki on (repository Settings → Features → Wikis), open the Wiki tab, click \"Create the first page\" and save it, then run this again."; return 1
  fi
  for f in "$TMP/wiki"/*.md; do [ -f "$f" ] && [ ! -f "$W/$(basename "$f")" ] && rm "$f"; done
  cp "$W"/*.md "$TMP/wiki/"
  G() { git -C "$TMP/wiki" -c core.autocrlf=false -c core.safecrlf=false "$@"; }
  G add -A
  if G diff --cached --quiet; then echo "The GitHub wiki already has these pages."; return 0; fi
  G status --short
  [ "$1" = "--dry-run" ] && { echo "Dry run: nothing pushed."; return 0; }
  G commit -q -m "Wiki update $(date +%Y-%m-%d)" && G push -q && echo "Published to $url"
}

case "${1:-status}" in
  status) status ;;
  mark) mark ;;
  publish) publish "$2" ;;
  *) sed -n '2,7p' "$0"; exit 2 ;;
esac
