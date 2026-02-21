with open("main.py", "r") as f:
    main_py_lines = f.readlines()

with open("strategies/strategy_generalized_hybrid.py", "r") as f:
    hybrid_lines = f.readlines()

start_idx = -1
for i, line in enumerate(main_py_lines):
    if line.startswith("def _call_cactus_single("):
        start_idx = i
        break

start_hybrid_idx = -1
for i, line in enumerate(hybrid_lines):
    if line.startswith("def _call_cactus_single("):
        start_hybrid_idx = i
        break

if start_idx != -1 and start_hybrid_idx != -1:
    new_main_py_lines = main_py_lines[:start_idx] + hybrid_lines[start_hybrid_idx:]
    with open("main.py", "w") as f:
        f.writelines(new_main_py_lines)
    print("Successfully patched main.py")
else:
    print("Failed to find boundaries")
