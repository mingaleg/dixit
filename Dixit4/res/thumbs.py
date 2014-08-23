from os import system
from os import listdir

cnt = 0

print(listdir('.'))
for suka in listdir('.'):
    if suka.endswith('.png'):
        system(r'convert "' + suka + '" -gravity NorthWest -resize x160 "thumbs/' + suka + '"')
