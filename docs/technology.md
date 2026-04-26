# Technology Stack

Aegis Stack is built on the shoulders of giants. Each tool was thoughtfully selected for its excellence in solving specific problems, and for how well it composes with others.

## The Sebastián Ramírez Ecosystem

### [FastAPI](https://fastapi.tiangolo.com/)

What can I say about FastAPI... Well, I remember the first time I heard the name from a co-worker, I slacked them back "That's a pretty pretentious name :)".

I won't waste your time with all the platitudes, you already know them all. What makes FastAPI special to me is that it answered a question that had bothered me my entire career... "Why do things always have to be so difficult?" I'd already been headed down the DX path without knowing what to call it, but FastAPI was the first concrete example of what it meant for me.

Intentional IDE support was the one that stood out to me, especially because I had just switched from barebones emacs to vscode. Realizing that all of these little decisions were made to make my life easier was really inspiring for me.

### [Typer](https://typer.tiangolo.com/)

When you find someone whose work resonates with you, you pay attention to what else they build. After FastAPI, Typer was an easy choice - same type-driven philosophy, same focus on making CLI commands feel like natural Python functions.

## The Pydantic Ecosystem: Defensive Coding as Philosophy

### [Pydantic](https://docs.pydantic.dev/)

I discovered Pydantic at the same time as FastAPI. We were doing one of those polyrepo → monorepo migrations to pad someone else's resume. Each app implemented the same message-based framework we'd created ([Henson](https://henson.readthedocs.io/)). We swapped our dictionary-based message validation for Pydantic.

For me at the time, it was just another validation framework.

Then I saw an interview with Samuel Colvin where he said something along the lines of "type hints are wasted, not doing anything" or something to that effect. This hit different.

Ever since I started using Python in 2012, coming from the Java world, it was crazy to not have types. I'll never forget one of the best Python programmers I've ever known responding to my concerns with **"We're all adults here."**

<img src="../images/not-sure-if.gif" alt="Not sure if serious" width="300">

So all of this is going on at the same time I'm using Pydantic models to build FastAPI APIs, and it's all starting to click together.

I was also leading a team of 10+ developers at this point, and it became very apparent very quickly how important defensive coding was. Being able to protect ourselves from ourselves became my mission.

Then when I saw Pydantic do a rewrite in Rust for V2, I knew they were serious. This wasn't just a validation library - this was infrastructure.

I've always been a paranoid developer, so having Pydantic at every part of the system became core to everything I write. It's also why I love Flet - with Python and only Python, that means the same Pydantic models for validation at API endpoint and client level. One source of truth, validated everywhere.

Then again, maybe I just have PTSD from dealing with a codebase full of dicts with string keys :)

### [Logfire](https://pydantic.dev/logfire)

When I saw Pydantic was doing Logfire, and it just "worked" - again, that same DX - it showed what a great developer experience should be. No fighting with configuration, no cryptic errors, just observability that gets out of your way.

### [Pydantic AI](https://ai.pydantic.dev/)

Pydantic AI was a breath of fresh air. I had that "Okay cool, the adults are here" moment in the AI framework wars. No disrespect to the others, but the pedigree here is massive. When the people who built the data validation layer that powers half of modern Python decide to tackle AI frameworks, you pay attention.

## The Foundation

### [Flet](https://flet.dev/) by Feodor Fitsner

Ah, Flet... The latest in my attempt to avoid learning "proper" frontend development. I'll never forget the day I saw a YouTube video on it, and thought "Oh shit, this is it!!! This is my salvation!". This was late 2023.

I had been building data dashboards and internal tools with Streamlit for years - excellent for rapid prototyping and visualization. But when I wanted to build full-featured applications with complex UIs, I needed something designed for general-purpose apps, not data-focused dashboards.

Flet was the first time in my career I felt like I could build complete web applications myself - production-grade UIs, not just quick prototypes.

It was the missing piece that finally let me use all those backend skills - FastAPI, Pydantic, everything - to ship actual products people could use.

Also, allows me to live out my fantasy of Python, python, and nothing but python, so help me god :)

## The Astral Revolution

### [ruff](https://docs.astral.sh/ruff/), [uv](https://docs.astral.sh/uv/), [ty](https://docs.astral.sh/ty/), [uvx](https://docs.astral.sh/uv/guides/tools/)

I was in my "Rust + Python is cool" phase when I tried ruff. Performance curiosity, mostly.

Then came uv. It was so fast I wasn't sure if it actually did anything. Seriously - I had to double-check that packages were actually installing. I went all-in immediately.

The progression was natural: ruff → uv → ty → uvx. Each one just worked. Fast. Really fast.

**Then uvx hit me.**

I'd been thinking about the onboarding problem - how do you let someone try a CLI tool without making them commit to installation? pip install, virtual environments, path configurations... death by a thousand cuts before they even see if they like it.

uvx changed the game completely: `uvx aegis-stack init my-project` - that's it. No installation. No setup. No "did I add this to PATH correctly?" They can test drive Aegis Stack RIGHT NOW, generate a project, kick the tires, and decide if it's for them. Five minutes from discovery to working code.

The moment I understood this, I dropped everything. "I GOTTA IMPLEMENT THIS NOW." Thank god I got that namespace :)

This is the difference between "check out this framework, here's the 47-step installation guide" and "just run this one command and see for yourself." That's not just convenient - that's the difference between someone trying your tool and someone scrolling past it.

uvx is DX for my users, not just me. It respects their time. They can evaluate Aegis Stack without the commitment, without the friction, without wondering if they're going to spend an hour just getting it installed.

And if they don't like it? No cleanup. No virtual environments to delete. No "how do I uninstall this?" It's like they were never there.

**That's the power of the Astral ecosystem** - they're not just making tools faster, they're removing the friction that stops people from even trying new things.

## The Pattern

<img src="../images/greivous.gif" alt="General Greivous" width="300">

I don't collect tools - I collect ecosystems. When I find creators who demonstrate consistent philosophy, proven execution, and genuine care for developer experience, I don't just adopt one tool. I watch what else they build, because chances are it'll solve problems I'm already facing or will face soon.

This is how experienced developers actually select technology: not by feature comparison spreadsheets, but by recognizing excellence and betting on the people who consistently deliver it.

Aegis Stack is the result of that pattern recognition made concrete - a platform built on ecosystems I trust, configured in ways I've battle-tested, ready for you to build on.
