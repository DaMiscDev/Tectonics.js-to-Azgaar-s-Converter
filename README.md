This script needs a specific Anaconda enviroment to run in, ortherwise it won't run. If you have Anaconda already installed, run this command in the terminal
conda create -n mapenv python=3.11 numpy=1.26 matplotlib pandas tk conda activate mapenv
This was developed on Apple, so I don't know how to set this up on Windows

You will have to clean up the csv file exported from Tectonics.js in order for the script to function. It should look like the csv example in the repository.
