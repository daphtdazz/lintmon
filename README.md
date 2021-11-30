# dirmon

A **dir**ectory **mon**itor. Provides a configurable way to specify checks to run on code in a given directory when it changes on disk, run those checks in the background and provide a fast way to display the outcome of the latest checks with a concise format suitable for embedding in your prompt.

## Motivation

The two main ways of avoiding pushing lint errors to a repo it seemed to me were:

1. lint on save in your IDE
2. add git hooks on push to check for / fix lint errors

I didn't like either of those, because in both cases they happen synchronously while you are doing something and can cause disruptions. Also I push from the command line, so what I wanted was a warning at the point that I was going to push that was pre-calculated about errors.

This is that.

## Configure

Install dirmon using `pip` in your virtualenv (or wherever you install packages for use with your codebase):

    pip install dirmon

Add a file like the dirmon.yaml file in this codebase to the root directory of your codebase. It tells dirmmon what checks to do on files. It aims to be very configurable.

Add the following to your prompt in your `.bashrc` or `.zshrc`:

    PS1='$([[ -e dirmon.yaml ]] && which dirmon-status-prompt >/dev/null && dirmon-status-prompt)'$PS1

That's it! `dirmon-status-prompt` will start `dirmond` automatically in the background when it is run, and from now on you should get a "badge" in your prompt when there are lint errors in your directory, which will be updated when you modify files.

## Commands

### `dirmon-status`

Output status of dirmon along with all current errors from the linters.

### `dirmon-stop`, `dirmon-start`

Tell dirmon to stop (and not restart automatically) or start again. Mostly useful for debugging dirmon. This will display an ` S ` badge in your prompt to tell you it is stopped.

### `dirmon-run-all`

Run all linters on all appropriate files in your project, thus "hydrating" dirmon's state if it hasn't been running for a while and changes have been made.

### `dirmond`

Run the daemon in the shell (again mainly useful for debugging).


## Directory structure

dirmon adds a `.dirmon` directory to your project directory where it stores all its state about what current errors there are, dirmon's pid etc. You will probably want to add this to your .gitignore.
