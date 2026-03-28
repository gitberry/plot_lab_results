# Plot Lab Results from JSON using Python

Python script that will produce tsv and charts from medical laboratory results. 

Current version called from command line and does this:

1. parse med lab JSON results (read below for caveats)
1. display unique list of tests contained within it
1. allow the user to specify just certain tests or all
1. for each test selected
   1. export the test results to a tsv (tab seperated)
   1. create a plot
      * shows red for items not within range information provided in data.
1. each graph will use information from reference.tsv to provide: 
   1. a "bucket" to group tests (ie PSA tests all together like a panel)
   1. extra information about what the test may be used for in a clinical setting

An extra python script (pdf_the_charts.py) can be used to create a PDF for printing ease.

## Getting Started
If you're a pythonista you can skip this section. 

### Virtual Python Environment
Recommended you lean about virtual environments for python and use them. This example was done using Poetry.

Unsolicited Advice: If this is the ONLY project you run on your machine - maybe you'll be OK - but otherwise you're just asking for dependency version hell over time and over projects. 

### Dependency Manager
I used Poetry - and set up my dependencies for pandas matplotlib seaborn pydantic using it. 

# Data

## JSON Data
This example was originally done on my own personal data - and then I built a file for a single lab test (Glucose) that was completely made up data indended to demonstrate the various features of the code (ie range info with warnings in red)  and not demonstrate anything realistic.

I'm not a doctor and even if you have fancy charts - you should still consult with a doctor if you have any concerns with your data - or not - your doctor may really like the instant chart of test results over time as much as you do!

You'll need to get your JSON data and that really depends on your situation. 
- JSON is typically how frontend code (ie the web page that is in "front" of you)
receives data from a 
- "backend" (ie the internet URL that serves up just boring ol' data)

You are on your own on this - if you press F12 on your browser and see something like "GET" and under it a Response that looks like JSON (look at the example_file.json for a crude idea) then you might be lucky!

Othewise - you may be spending a lot of time getting the data in a form that is useful. 

Good luck!

## Reference Data

The reference data was collected with a few keystrokes on a google - and it's purpose is to help with few things:
  1. groups tests - for example the PSA test by my providor were upgraded over time so they need to be grouped to get full picture. 
  1. top title - for grouped or oddly named tests - this could be handy.
  1. a safe suitable name for the artifacts - (since test names amy include odd characters)
  1. a little note about what a test may be used for in a clinical environmen (very handy quick reference)

### Dependencies

* pandas 
* matplotlib 
* seaborn 
* pydantic

Quick CLI command if you use poetry:
```bash
poetry add pandas matplotlib seaborn pydantic
```

# Executing program

This has only been tested on a linux environment - theoretically it should work on windows with python installed.

## general usage: 

Since I used poetry - my command was this:

```bash
poetry run python3 main.py file.json reference.tsv
```

 - file.json: your data from whatever source you got it from 
 - reference.tsv: 
   provided in this project (see ### Reference Data Above)

If you're all geeky - you may want to keep the screen output in a log - so this is the way to do that:

```bash
poetry run python3 main.py file.json reference.tsv 2>&1 | tee output.log;. cleanup.txt;
```

## Authors

This little script was created by Clark Rensberry while using all the free LLM's to learn more about various python features.

## Version History

* 0.1
    * 2026.03.27 Basic data collection, chart creation and pdf collation of charts from Laboratory portal JSON data

### TODO
* make svg and pdf generation integrated. 
* make suitable for small screen
* research secure generation for mobile