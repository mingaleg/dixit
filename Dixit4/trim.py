from os import system
from os import listdir

cnt = 0

print(listdir('.'))
for suka in listdir('.'):
    if suka.endswith('.jpg'):
        cnt += 1
        system(r'convert "' + suka + '" -gravity SouthEast -crop 50%x100% res/' + str(cnt) + '.png')
        print(cnt)
        cnt += 1
        system(r'convert "' + suka + '" -gravity NorthWest -crop 50%x100% res/' + str(cnt) + '.png')
        print(cnt)
