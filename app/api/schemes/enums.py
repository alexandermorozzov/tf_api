from enum import Enum, auto

class AvailableRegions(str, Enum):
    lo = "Ленинградская_область"
    vo = 'Волгоградская_область'
    kk = 'Краснодарский_край'
    m = 'Москва'
    mo = 'Московская_область'
    oo = 'Омская_область'
    spb = 'Санкт-Петербург'
    tuo = 'Тульская_область'
    tumo = 'Тюменская_область'

class Level(str,Enum):
    region = 'region'
    district = 'districts'
    settlements = 'settlements'
    territory = 'territory'