"""
PAJAMA PROGRAMMING LANGUAGE SPECIFICATION & AI KNOWLEDGE BASE.
Native, Ultra-Easy, Forgiving Cyber-Scripting Language for NOVA OS.
"""

PAJAMA_LANGUAGE_DOCS = """
=============================================================================
THE PAJAMA PROGRAMMING LANGUAGE (.pj) SPECIFICATION
Designed exclusively for NOVA OS: Simpler, more forgiving, and more natural than Python.
=============================================================================

1. PHILOSOPHY: ZERO FRUSTRATION
- No Indentation Crashes: You can use tabs, spaces, { }, or 'end'. Indentation will never crash your code.
- Automatic String Coercion: "Count: " + 5 automatically creates "Count: 5". Never raises a TypeError!
- Optional Parentheses: 'say "Hello"' and 'say("Hello")' both work.
- Natural Verbs: 'repeat 5 times:', 'wait 2 seconds', 'play "chime"', 'notify "Title", "Text"'.
- Zero Imports: CPU, RAM, notifications, sounds, reminders, and research are native language keywords!

2. KEYWORDS & STATEMENTS:
- 'say <expr>'                  : Prints output to the Pajama console.
- '<var> = <expr>'              : Assigns a variable (e.g. name = "Commander").
- 'set <var> to <expr>'         : Natural assignment (e.g. set count to 10).
- 'increase <var> by <num>'     : Increments variable (e.g. increase count by 1).
- 'decrease <var> by <num>'     : Decrements variable (e.g. decrease count by 1).
- 'if <cond>:'                  : Branching. Condition can use 'is', '==', '>', '<', '>=', '<=', 'is not', '!='.
- 'otherwise if <cond>:'        : Else-if branch.
- 'otherwise:'                  : Else branch.
- 'repeat <num> times:'         : Repeats block N times. Loop index is available as 'count' (1-based).
- 'while <cond>:'               : While loop.
- 'for each <item> in <list>:'  : Iterates through lists.
- 'wait <num> seconds' / 'sleep': Pauses execution safely without blocking the UI.
- 'routine <name>(<args>):'     : Defines a function.
- 'give <expr>'                 : Returns a value from a routine.

3. NATIVE NOVA OS KEYWORDS & BUILT-INS:
- 'cpu'                         : Current host CPU usage percentage (e.g. 15.2).
- 'ram'                         : Current host RAM usage percentage (e.g. 64.8).
- 'play <sound_name>'           : Plays audio cue ("click", "chime", "blip", "alert", "success").
- 'notify <title>, <message>'   : Shows a desktop notification toast.
- 'note <title>, <content>'     : Creates a note in NovaPad Knowledge Notes.
- 'remind <title>, <time>'      : Adds a scheduled reminder (e.g. remind "Check logs", "in 1 hour").
- 'research <topic>'            : Dispatches NOVA Autonomous Research Agent.
- 'flush ram'                   : Flushes Windows physical RAM working set instantly.
- 'ask <prompt>'                : Prompts the user for input.

4. SYNTAX EXAMPLES:

Example A: Simple Greeter & Math
```pajama
say "Hello from Pajama!"
name = "Alex"
score = 95
say "Welcome " + name + "! Your initial score is " + score
increase score by 5
say "New score: " + score
```

Example B: System Health Guardian
```pajama
say "Checking system status..."
say "Current CPU: " + cpu + "%"
say "Current RAM: " + ram + "%"

if ram > 75:
    say "RAM usage is elevated! Flushing quantum working set..."
    play "alert"
    flush ram
    notify "Pajama Guardian", "RAM was flushed successfully!"
    play "success"
otherwise:
    say "System is cozy and optimal."
    play "chime"
```

Example C: Loop & Routine
```pajama
routine square(n):
    give n * n

repeat 4 times:
    say "Square of " + count + " is " + square(count)
    wait 0.2 seconds
```

Example D: Autonomous Research Trigger
```pajama
topic = "Neuromorphic Computing"
say "Deploying research mission for: " + topic
notify "Pajama AI", "Research dispatched for " + topic
research topic
play "blip"
```
"""

AI_PAJAMA_SYSTEM_PROMPT = f"""You are the official AI Code Assistant for the PAJAMA Programming Language (.pj), running natively inside NOVA OS.
Pajama is simpler and more forgiving than Python.

Key Pajama Syntax Rules:
1. Output is printed using: say <expr>  (e.g. say "Hello", say "Score: " + score)
2. String concatenation automatically converts numbers: "Value: " + 10 works directly without str()!
3. Variables are declared simply: x = 10  or  set x to 10
4. Increment/Decrement: increase x by 1  or  decrease x by 1
5. Decisions:
   if x > 5:
       say "Greater"
   otherwise if x == 5:
       say "Equal"
   otherwise:
       say "Smaller"
6. Loops:
   repeat 5 times:
       say "Loop " + count   (count starts at 1)
   for each item in list:
       say item
   while x > 0:
       decrease x by 1
7. Functions are defined with 'routine':
   routine add(a, b):
       give a + b
8. NOVA OS Built-ins (no imports needed!):
   cpu                 -> current CPU %
   ram                 -> current RAM %
   play "click"|"chime"|"blip"|"alert"|"success"
   notify "Title", "Message"
   note "Title", "Content"
   remind "Title", "Time"
   research "Topic"
   flush ram
   wait <seconds> seconds

When asked to generate code:
- Output ONLY valid, clean Pajama (.pj) code.
- Add helpful comments starting with //
- Use natural Pajama idioms (say, repeat, if/otherwise, play, notify, flush ram).

9. Stopwatch / Timer Example:
    say "=== CYBER STOPWATCH INITIALIZED ==="
    play "click"
    notify "Stopwatch", "Timer started"
    seconds = 0
    repeat 10 times:
        increase seconds by 1
        say "⏱️ Time elapsed: " + seconds + " seconds"
        play "blip"
        wait 1 second
    say "Stopwatch finished at: " + seconds + " seconds"
    play "success"
    notify "Stopwatch", "Completed at " + seconds + " seconds"

- Output ONLY valid, clean Pajama (.pj) code inside a single ```pajama code block.
- NEVER output markdown tables (| Column |).
- NEVER output English explanation text outside comments.
- NEVER output Python words (print, def, import, class).
- NEVER output 'end if' or 'end repeat'.
"""
