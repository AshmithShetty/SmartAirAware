import sys
from eppy.modeleditor import IDF

iddfile = r'C:\EnergyPlusV26-2-0\Energy+.idd'
fname = r'data\building.idf'

IDF.setiddname(iddfile)
idf = IDF(fname)

schedule = idf.getobject('SCHEDULE:COMPACT', 'CLGSETP_SCH')
if schedule:
    print(f'Success! Found Cooling Setpoint Schedule: {schedule.Name}')
    idf.saveas(r'data\building_modified.idf')
    print('Saved test modification to data/building_modified.idf')
else:
    print('Schedule not found.')
