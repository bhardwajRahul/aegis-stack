# How I Build

Very early on in the development of Aegis Stack, I knew I wanted to do what had just never been possible for me (except early in my career): true Test Driven Development (TDD). I like to move fast, make changes, revert them, refactor them, within days. TDD gives me that ability.

I have a test file that does nothing but spin up different component combinations. Scheduler + Worker. Auth + AI. Database + Worker + Scheduler. All of them. Why? Because I'm paranoid.

I've also seen a lot of shit. There have been way too many "Fuck, if only we had tests" moments in my career. Well, I'm done with that life.

**So, it's nothing crazy. It's just this:**

1. Generate a fresh project with specific components
2. Install its dependencies
3. Run lint, typecheck, and its tests
4. Validate the structure matches what I expect

That's it. No mocks. No elaborate test fixtures. Just "does the generated project actually work?"

The test suite spins up every valid combination...base stack, scheduler, worker, full stack with everything. Each one gets validated from scratch. If I break something in the template, I know within seconds because one of the 6 combinations fails.

## Why This Works

The secret is the architecture. Because everything is template-driven and modular, testing is just regeneration + validation. The templates ARE the product.

When I added the scheduler component, I followed the same pattern as worker. Auth service? Same pattern. AI service? Same pattern. Each time, the tests validated it worked with every other component—not just in isolation, but in combination.

Here's the thing that surprised me: adding new components gets *easier* over time, not harder. That's the foundation. Not "good enough for now" code that becomes technical debt. Actual tested, validated, proven patterns I can build on with confidence.

Fast iteration requires solid ground. The paranoid testing gives me that ground. And when I have that ground, I can take more risks:

![Peace](images/eli_to_manningham.gif)
