<p align="center">
  <h1 align='center'><b>FLOW</b></h1>
  <p style="font-size: 16px;" align='center'><u>F</u>unction, <u>L</u>anguage, & <u>O</u>bject <u>W</u>orkflow notation</p>
</p>

FLOW is a *tiny* language meant for AI-native workflows.  
It is designed for a specific job: creating safe, reliable, and easy-to-review automations.

Most general-purpose languages are great at many things, but that breadth creates overhead -- leading to high cognitive complexity, and too much room for unsafe or fragile behavior.

FLOW takes the opposite approach: one command per line, a small, explicit command set (`GET`, `LLM`, `OUTPUT`, etc.), clear control flow (`IF`, `ELSE`, `RETURN`), and so-easy-it's-dumb composition (`SCRIPT`).

## Core Message

***AI Automation gets smarter when we abstract away the specifics.***

> Think about styling: You *could* tell an LLM to write CSS manually, but *Tailwind* made it faster, and *shadcn* is so efficient it's possible to now one-shot entire UIs in one readable file.

FLOW applies that same principle to automation. *When most workflows consist of basic REST commands and LLM calls, why are we using entire, general-purpose languages to write them?*

## Quickstart

- Start here for setup and first run: [QUICKSTART.md](QUICKSTART.md)
- Full language docs (for humans and LLMs): [FLOW_LANGUAGE_REFERENCE.md](FLOW_LANGUAGE_REFERENCE.md)
- Ready-made [examples](examples/)

## Current Project Status

This repository is an evolving implementation of the FLOW interpreter and language docs.  
The command model is intentionally small and focused on practical automation scenarios.