# macOS App Build Pipeline Design

## Goal

Provide one repeatable local command that builds the GUI as a native macOS application bundle on Apple Silicon. The pipeline must produce a verified `Md2docx.app` without Nuitka onefile extraction, preserve the last successful application when a build fails, and remain extensible for future Developer ID signing, notarization, and DMG packaging.

The initial scope is local arm64 development builds. Public distribution, universal binaries, Intel-only builds, Apple notarization, and CI-hosted macOS builds are explicitly deferred.

## Command Interface

The existing `scripts/build_nuitka.py` remains the single build entry point. It gains an `app` mode for the GUI:

```bash
uv run --group build python scripts/build_nuitka.py --entry gui --mode app
```

The supported local controls are:

- `--clean`: remove Nuitka intermediate output before compilation.
- `--skip-tests`: bypass the pre-build test suite for temporary development iterations.
- `--launch`: open the verified application after a successful build.

`--mode app` is valid only for `--entry gui` on macOS. Existing `onefile` and `standalone` behavior remains available for the GUI and CLI so the change does not remove current workflows.

## Pipeline Stages

The build script runs these stages in order:

1. **Preflight** checks the host platform, arm64 architecture, Nuitka availability, source entry point, packaged template, and output locations. A dirty Git worktree is reported but does not block a local build.
2. **Tests** run the repository test suite with the active uv-managed Python environment unless `--skip-tests` is present.
3. **Preparation** creates intermediate and staging directories. With `--clean`, only known Nuitka intermediate paths are removed.
4. **Compilation** invokes Nuitka with `--macos-create-app-bundle`, the `tk-inter` plugin, md2docx package data, and Mistune plugin inclusion. App mode never enables onefile.
5. **Staging** copies the completed application to a temporary directory under `dist/macos` and places an editable `default.yaml` beside it.
6. **Verification** validates the bundle structure, executable architecture, packaged resources, Tcl/Tk runtime, and local code signature.
7. **Promotion** replaces `dist/macos/Md2docx.app` only after all verification passes. The previous successful app remains untouched on earlier failures.
8. **Summary** reports the final paths, application size, elapsed time, and whether tests, cleaning, and launch were requested.

The default flow does not launch the GUI. `--launch` runs the macOS `open` command only after promotion succeeds.

## Components And Boundaries

The orchestration remains in `scripts/build_nuitka.py`, split into small functions with explicit inputs and outputs:

- `preflight_macos_app()` validates platform-specific requirements.
- `run_test_suite()` runs tests and propagates failures.
- `build_target()` constructs and executes the Nuitka command.
- `stage_macos_app()` prepares the candidate release directory.
- `verify_macos_app()` performs post-build checks without modifying source files.
- `promote_macos_app()` publishes the verified candidate.
- `launch_macos_app()` implements the optional launch step.

Generic executable naming and existing onefile/standalone behavior stay platform-neutral. macOS bundle knowledge is confined to the app-specific functions so future signing and packaging stages can be added without complicating Windows builds.

## Output And Resource Layout

Intermediate compiler output stays separate from user-facing artifacts:

```text
build/nuitka/                  Nuitka compiler output and reusable cache
build/logs/                    Build diagnostics
dist/macos/
├── Md2docx.app                Last verified application
└── default.yaml               Editable example configuration
```

The packaged `md2docx/templates/default.yaml` remains inside the application and is the reliable startup fallback. The external `dist/macos/default.yaml` is an editable example that can be opened through the GUI; the app does not depend on it being present. User preferences and conversion history remain under `~/.md2docx`.

The app bundle uses standalone loading. Finder presents the bundle as one application, but its libraries and resources remain available in place, avoiding the decompression and temporary-directory extraction required by onefile mode.

## Failure Handling

Every failed stage returns a non-zero process exit code and identifies the stage in the error message. Expected failures include unsupported platform or architecture, missing inputs, test failure, Nuitka failure, missing bundle files, incorrect architecture, absent Tk resources, and invalid local signing.

Compiler output is streamed to the terminal and retained in `build/logs`. Failed candidates remain available under a clearly named staging directory for diagnosis. The script never deletes arbitrary user paths and never removes the last promoted app before a replacement has passed verification.

Local builds use or refresh an ad-hoc macOS signature and verify it with `codesign --verify`. Developer ID identities and Apple credentials are not read in this version.

## Verification Strategy

Unit tests live in a dedicated build-script test module and avoid invoking a real compiler. They cover:

- argument combinations and app-mode platform restrictions;
- generated Nuitka flags, including the absence of onefile mode;
- deterministic intermediate, staging, and final paths;
- clean-path allowlisting;
- failure propagation from tests and Nuitka;
- verification failures for missing bundle files, wrong architecture, missing resources, and invalid signatures;
- preservation of the previous successful app when staging or verification fails;
- promotion only after successful verification.

The default pipeline also runs the existing repository tests before compiling. A real local acceptance build verifies:

- `dist/macos/Md2docx.app/Contents/Info.plist` exists;
- the executable under `Contents/MacOS` is arm64;
- packaged md2docx templates and Tcl/Tk resources exist;
- `codesign --verify --deep --strict` succeeds;
- the final artifact is an app bundle rather than a onefile executable;
- `--launch` can open the promoted app when explicitly requested.

## Acceptance Criteria

The design is complete when a developer on an Apple Silicon Mac can run the documented uv command repeatedly and receive a verified `dist/macos/Md2docx.app`. A failed test, compilation, or verification must leave the previous successful app usable. The default app launch must not perform Nuitka onefile extraction, and no Apple Developer credentials may be required for the local workflow.
