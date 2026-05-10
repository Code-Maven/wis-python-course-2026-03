# Copilot Instructions for this Repository

## Project Overview
- This repository contains materials and assignment examples for the WIS Python course (2026-03).
- Content is organized by lecture day in folders named `day01`, `day02`, ..., `day05`.
- Most files are small, standalone teaching scripts that demonstrate one concept at a time.

## Primary Goals for Generated Code
- Keep code beginner-friendly and easy to read.
- Prefer clear, explicit solutions over clever or highly abstract ones.
- Keep each script focused on one task.
- Preserve educational value: examples should be simple to explain in class.

## Repository Structure Conventions
- Put new exercise files in the correct `dayXX` folder.
- Avoid moving or renaming existing lesson files unless explicitly requested.
- Use top-level markdown files (`README.md`, `SYLLABUS.md`, `DAYS.md`) as source of course context.

## Python Style Expectations
- Use Python 3 with type hints where practical.
- Use descriptive function names and small functions.
- Add argument parsing (`argparse`) for command-line scripts when input parameters are needed.
- Use standard library first; add third-party dependencies only when they are clearly useful for the lesson.
- Keep output messages concise and student-friendly.

## Testing and Safety
- If editing logic, suggest or add simple tests when a test file already exists for that topic.
- Validate file paths and input assumptions with clear error messages.
- Do not introduce destructive behavior (for example deleting user files) unless explicitly asked.

## Day-Specific Context (Current Content)
- Early days focus on basic syntax, control flow, simple functions, and text processing.
- `day03` includes introductory testing (`test_area_of_rectangle.py`).
- `day05` includes file and data tasks (CSV, Excel, image download/display) and uses libraries such as `pandas` when appropriate.

## Preferred Response Behavior in This Repo
- When generating code changes, keep diffs minimal and localized.
- Preserve existing naming and folder patterns.
- Include short usage examples for command-line scripts when helpful.
