# The 17,045 judge build

Drop the four deployed files here exactly as they are in the console, no edits:

    codeexecution-lambda.py
    pathfinding-lambda.py
    websearch-lambda.py
    supervisor-prompt.txt

Why: this build scored **17,045 on the judge**. The current build scores 17,044 on the
test map but only 16,181 on the judge - an 864-point judge-only regression. Both builds
behave the same on the test map, so the difference is only visible by diffing them.

Once these are here, `diff_known_good.py` reports every behavioural difference: flag
values, handler outputs for the same payloads, and prompt rules present in one and not
the other. That turns a guess into a list.
