"""brand_named.py - companies that get their own entry in the logo menu.

Their real logos aren't free to share, so each one is drawn with the matching
HushKey icon (a plane for airlines, a bank for banks...) in the company's own
color when it's known, and shows under its own name: searching "Frontier"
finds "Frontier Airlines", not just "Airline".

One company per line:   Name | color (optional) | other names; separated; by semicolons
Companies that already have a real logo in Simple Icons are skipped automatically.
"""

NAMED = {
    "hk-plane": """
Frontier Airlines | 249A4C | frontier; flyfrontier; frontier air
Alaska Airlines | 01426A | alaska; alaskan airlines; alaskan airline; alaska air; mileage plan; atmos rewards
Spirit Airlines | D4B500 | spirit; free spirit
Allegiant Air | F7941D | allegiant; allegiant airlines
Sun Country Airlines | F5A800 | sun country
Breeze Airways | 00A3E0 | breeze
Avelo Airlines | 6A2C91 | avelo
Hawaiian Airlines | 5C2D91 | hawaiian; hawaiianmiles
Contour Airlines
Silver Airways
Cape Air
Mokulele Airlines
Southern Airways Express
Boutique Air
Advanced Air
SkyWest Airlines | | skywest
Republic Airways
Envoy Air
Endeavor Air
Piedmont Airlines
Horizon Air
Mesa Airlines
PSA Airlines
GlobalX
WestJet | 00A3AD | westjet rewards
Porter Airlines | 1B365D | porter
Flair Airlines | | flair
Air Transat | | transat
Sunwing
Pacific Coastal Airlines
Volaris | A12385
Viva Aerobus | 00A84F | viva
Aeromar
LATAM Airlines | 1B0088 | latam
Azul Brazilian Airlines | 0057A8 | azul
GOL Linhas Aereas | FF6600 | gol
JetSMART | | jetsmart
Sky Airline
Arajet
Wingo
Flybondi | E5B800
Aerolineas Argentinas | 0A7CC1
Boliviana de Aviacion
Paranair
Caribbean Airlines
Bahamasair
InterCaribbean Airways
Cayman Airways
Vueling | E0A800
Volotea
Transavia | 00B050
Eurowings | A3195B
Condor | E8A400
Jet2 | D50000 | jet2holidays
TUI Airways | | tui
PLAY Airlines | | play
Icelandair | 01486F
Aer Lingus | 006272
Loganair
Binter
Air Europa
Iberia Express
LEVEL
SAS Scandinavian Airlines | 000099 | sas; eurobonus
Finnair | 0B1560
airBaltic
LOT Polish Airlines | | lot
Smartwings
Pegasus Airlines | E0A800 | pegasus
SunExpress
AJet
Aegean Airlines | | aegean
SKY express
Croatia Airlines
Air Serbia
TAROM
SWISS International Air Lines | E20613 | swiss
Edelweiss Air
Austrian Airlines | E2001A | austrian
Brussels Airlines
ITA Airways
Luxair
Discover Airlines
Corendon Airlines
Neos
Wideroe
Braathens
Blue Air
flydubai | | fly dubai
Air Arabia
flynas
flyadeal
Saudia
Jazeera Airways
SalamAir
Oman Air
Gulf Air
Kuwait Airways
Royal Jordanian
Middle East Airlines
El Al | | elal
Israir
Arkia
EgyptAir
Royal Air Maroc
Ethiopian Airlines
Kenya Airways
RwandAir
FlySafair
Airlink
Air Peace
Air Mauritius
Cathay Pacific | 006564 | cathay; asia miles
HK Express
Korean Air | 154D8F | skypass
Asiana Airlines | | asiana
Jeju Air
Jin Air
T'way Air
Air Busan
Peach Aviation | | peach
ZIPAIR
Spring Japan
Skymark Airlines
StarFlyer
EVA Air | 006241
China Airlines
STARLUX Airlines
Tigerair Taiwan
Cebu Pacific | | cebu
Philippine Airlines
Scoot | E5C000
Jetstar | FF5115
Batik Air
Lion Air
Citilink
Garuda Indonesia
Malaysia Airlines
Firefly
Thai Airways
Thai Lion Air
Nok Air
Bangkok Airways
VietJet Air | | vietjet
Vietnam Airlines
Bamboo Airways
SpiceJet
Akasa Air
Air India Express
Biman Bangladesh Airlines
US-Bangla Airlines
SriLankan Airlines
Pakistan International Airlines | | pia
Airblue
Hainan Airlines
Xiamen Airlines
Sichuan Airlines
Spring Airlines
Juneyao Air
Virgin Australia | E10A0A
Rex Airlines
Bonza
Air New Zealand | | airpoints
Fiji Airways
Air Tahiti Nui
QantasLink
Kayak | FF690F
Skyscanner | 0770E3
Google Flights
Hopper
Priceline | 0068EF
Orbitz
Travelocity
CheapOair
Kiwi.com
Momondo
Going | | scotts cheap flights
Hotwire
Trip.com
Opodo
eDreams
lastminute.com
Kayak Business
TSA PreCheck
CLEAR | | clear plus
Global Entry
Flighty
FlightAware
Seatguru
""",
    "hk-train": """
Amtrak | 1D5F8A | amtrak guest rewards
Greyhound | 0D4F8B
FlixBus | 73D700 | flix
Megabus
Brightline
Peter Pan Bus Lines | | peter pan
OurBus
Wanderu
Busbud
Omio
Rome2rio
Trainline
Eurostar
National Rail
Avanti West Coast
LNER
Renfe
Trenitalia
Italo
SBB
OBB
NS
Via Rail
JR East
Japan Rail Pass
BlaBlaCar
Transit app | | transit
Moovit
Citymapper
Ventra
Clipper
OMNY
SmarTrip
TfL Oyster | | oyster; tfl
Lime
Bird
Citi Bike
Revel
Metro Transit
""",
    "hk-hotel": """
Hyatt | | world of hyatt
IHG Hotels | | ihg; ihg one rewards
Holiday Inn
Choice Hotels | | choice privileges
Wyndham | | wyndham rewards
Best Western
Accor | | all accor
Radisson
Four Seasons
Vrbo | 245ABC
Agoda
Hostelworld
Motel 6
La Quinta
Red Roof
Extended Stay America
Super 8
Days Inn
Comfort Inn
Quality Inn
Hampton Inn
Sonesta
Omni Hotels
Loews Hotels
Kimpton
Graduate Hotels
citizenM
Premier Inn
Travelodge
ibis
Novotel
HotelTonight
Sonder
Selina
Hotwire Hotels
Carnival Cruise Line | | carnival
Royal Caribbean
Norwegian Cruise Line | | ncl
Princess Cruises
Celebrity Cruises
MSC Cruises
Disney Cruise Line
Virgin Voyages
Holland America Line
Six Flags
Cedar Point
SeaWorld
Universal Orlando
Disneyland
Walt Disney World | | disney world
Great Wolf Lodge
KOA
Hipcamp
Recreation.gov
""",
    "hk-bank": """
Capital One | D03027 | capitalone
Citi | 056DAE | citibank
U.S. Bank | 0C2074 | us bank; usbank
PNC Bank | EF7622 | pnc
Truist | 5B3C88
TD Bank | 34A853 | td
Santander | EC0000
Ally Bank | 7B2A86 | ally
SoFi | 00A3E0
Chime | 1EC677
Varo Bank | | varo
Current
Navy Federal Credit Union | 1C3F94 | navy federal; nfcu
USAA | 1A3E6F
PenFed Credit Union | | penfed
Charles Schwab | 00A0DF | schwab
Fidelity | 368727
Vanguard | 96151D
E*TRADE | | etrade
Merrill | | merrill lynch; merrill edge
Morgan Stanley
Regions Bank | | regions
Fifth Third Bank | | fifth third
Huntington Bank | | huntington
Citizens Bank
KeyBank
M&T Bank
First Citizens Bank
Frost Bank
Synchrony Bank | | synchrony
Marcus by Goldman Sachs | | marcus
Axos Bank
One Finance
Albert
Aspiration
Upgrade
LendingClub
CIT Bank
Barclays US Savings
Bread Savings
Sallie Mae Bank
Laurel Road
Bluevine
Novo
Mercury
Lili
Found
Relay
Brex
Ramp
Green Dot
Netspend
GO2bank
Alliant Credit Union | | alliant
BECU
Golden 1 Credit Union | | golden 1
Suncoast Credit Union
America First Credit Union
State Employees Credit Union | | secu
DCU | | digital federal credit union
First Tech Federal Credit Union
Patelco Credit Union
Bethpage Federal Credit Union
Mountain America Credit Union
SchoolsFirst FCU
Randolph-Brooks FCU | | rbfcu
Security Service FCU
VyStar Credit Union
Teachers Federal Credit Union
Lake Michigan Credit Union
Global Credit Union
Delta Community Credit Union
GreenState Credit Union
Space Coast Credit Union
Wings Financial
Redstone FCU
Desert Financial
OnPoint Community Credit Union
Affinity Plus
Members 1st FCU
Ent Credit Union
Langley FCU
Coastal Credit Union
Logix
Star One Credit Union
BMO
Comerica
Zions Bank
Webster Bank
Associated Bank
Old National Bank
Valley Bank
Synovus
First Horizon
Cadence Bank
Arvest Bank
BancFirst
UMB Bank
Commerce Bank
Hancock Whitney
Trustmark
Simmons Bank
First National Bank
Bank OZK
Fulton Bank
Prosperity Bank
Wintrust
Eastern Bank
First Interstate Bank
Banner Bank
Umpqua Bank
East West Bank
Cathay Bank
Mechanics Bank
Woodforest National Bank | | woodforest
Chase UK
RBC Royal Bank | 005DAA | rbc; royal bank
Scotiabank | EC111A
CIBC | C41F3E
Desjardins
Tangerine
Simplii Financial
EQ Bank
National Bank of Canada
ATB Financial
KOHO
Wealthsimple
Lloyds Bank | 006A4D | lloyds
NatWest | 42145F
Halifax
Nationwide Building Society | | nationwide
TSB
Metro Bank
Virgin Money
Kroo
First Direct
Co-operative Bank
Bank of Scotland
Royal Bank of Scotland | | rbs
BBVA
ING
BNP Paribas
Societe Generale
UBS
Credit Agricole
La Banque Postale
CaixaBank
Raiffeisen
PostFinance
UniCredit
Intesa Sanpaolo
ABN AMRO
Rabobank
Nordea
Swedbank
Danske Bank
Handelsbanken
SEB
Itau
Bradesco
Banco do Brasil
Caixa
Westpac
Commonwealth Bank | | commbank
ANZ
NAB
Macquarie
Standard Chartered
DBS
OCBC
UOB
Maybank
CIMB
BDO
BPI
Kotak Mahindra Bank | | kotak
State Bank of India | | sbi
Axis Bank
Emirates NBD
QNB
Al Rajhi Bank
Garanti BBVA
Akbank
Banorte
Banamex
BBVA Mexico | | bancomer
""",
    "hk-card": """
Credit One Bank | | credit one
Mission Lane
Petal
Milestone Card
Indigo Card
Merrick Bank
OpenSky
Aspire Card
Avant
Destiny Card
First Premier Bank
Total Visa
Reflex Card
Fortiva
Upgrade Card
Apple Card
Target Circle Card | | target redcard
Kohl's Card
Macy's Card
Best Buy Card
Comenity
Bread Financial
Synchrony Card
Barclaycard
""",
    "hk-money": """
Crypto.com
Kraken
Gemini
Webull
eToro
Acorns
Stash
Betterment
Wealthfront
Public.com | | public
M1 Finance
Affirm | 4A4AF4
Sezzle
Zip
Splitwise
Quicken
YNAB
TurboTax
H&R Block
FreeTaxUSA
TaxAct
Credit Karma | 3BB54A
Experian
Equifax
TransUnion
Western Union
MoneyGram
Remitly
Xoom
Payoneer
Skrill
Neteller
MetaMask
Trust Wallet
Ledger Live
Exodus
Phantom
Blockchain.com
BitPay
Uphold
Bitstamp
Bybit
OKX
KuCoin
tastytrade
Interactive Brokers
Firstrade
Dave
Brigit
EarnIn
Empower
Rocket Money
Monarch Money
Copilot Money
Cleo
MoneyLion
Possible Finance
Klover
Self
Kikoff
Grow Credit
Upstart
Prosper
LendingTree
NerdWallet
Bankrate
Navient
Nelnet
MOHELA
Aidvantage
EdFinancial
Federal Student Aid | | fafsa; studentaid
Fundrise
Masterworks
Rocket Mortgage
Mr. Cooper
Freedom Mortgage
loanDepot
Better Mortgage
Social Security | | ssa; my social security
IRS
""",
    "hk-shopping": """
Temu | FB7701
SHEIN | 222222
Best Buy | 0046BE | bestbuy
The Home Depot | F96302 | home depot
Lowe's | 004990 | lowes
Menards
Ace Hardware
Harbor Freight
Tractor Supply
Northern Tool
Wayfair | 7F187F
Overstock
Chewy | 1C49C2
Petco
PetSmart
Nordstrom
Nordstrom Rack
Saks Fifth Avenue
Bloomingdale's
Neiman Marcus
JCPenney
Kohl's | 85003C
Dillard's
Belk
Williams Sonoma
Pottery Barn
Crate & Barrel
West Elm
Ashley Furniture
Rooms To Go
Kirkland's
At Home
Five Below
Ross Dress for Less | | ross
TJ Maxx | | tjmaxx
Marshalls
Burlington
HomeGoods
Ollie's
Big Lots
Old Navy
Gap
Banana Republic
J.Crew
Express
Lululemon
Foot Locker
Finish Line
JD Sports
Champs Sports
Dick's Sporting Goods
Academy Sports
REI
Bass Pro Shops
Cabela's
Urban Outfitters
American Eagle
Aerie
Abercrombie & Fitch
Hollister
Forever 21
ASOS
boohoo
Fashion Nova
PrettyLittleThing
Revolve
Romwe
Cider
Halara
Hot Topic
Zumiez
PacSun
Tillys
Torrid
Lane Bryant
Victoria's Secret
Bath & Body Works
Ulta Beauty | | ulta
Sephora
Sally Beauty
e.l.f. Cosmetics
Zappos
DSW
Famous Footwear
Skechers
Vans
Converse
Crocs
Steve Madden
Coach
Michael Kors
Kate Spade
Pandora Jewelry
Kay Jewelers
Zales
Jared
Fanatics
Lids
Build-A-Bear
GameStop
Michaels
JOANN
Hobby Lobby
Staples
Office Depot
Micro Center
B&H Photo
Adorama
Woot
Slickdeals
QVC
HSN
Poshmark
Mercari
OfferUp
Depop
Grailed
GOAT
ThredUp
The RealReal
Facebook Marketplace
Craigslist
Ibotta
Fetch Rewards | | fetch
Swagbucks
Capital One Shopping
Quince
Everlane
Primark
Argos
Currys
John Lewis
Next
Boots
Flipkart
Myntra
Meesho
Mercado Libre
Lazada
Tokopedia
Jumia
Noon
bol.com
Coolblue
Allegro
Trendyol
Coupang
JD.com
Tmall
DHgate
Banggood
""",
    "hk-cart": """
Walmart | 0071CE | walmart+
Costco | E31837
Kroger | 0068B3
Safeway
Albertsons
Whole Foods Market | 00674B | whole foods
Trader Joe's | D21242
Sprouts Farmers Market | | sprouts
Publix | 3F8F29
H-E-B | EE3124 | heb
Meijer
Wegmans
Food Lion
Giant Food
Stop & Shop
Harris Teeter
WinCo Foods
Fred Meyer
Ralphs
Vons
Jewel-Osco
ShopRite
Hy-Vee
Piggly Wiggly
Winn-Dixie
Save A Lot
Food 4 Less
Smith's
King Soopers
Grocery Outlet
Market Basket
Ingles
Weis Markets
Raley's
Stater Bros
Smart & Final
Cardenas Markets
Fiesta Mart
Northgate Market
Food Bazaar
Key Food
Hannaford
Price Chopper
Tops Markets
Schnucks
Festival Foods
Woodman's
Fareway
Dillons
QFC
Pick 'n Save
Mariano's
Lowes Foods
Dollar General | FFC220
Dollar Tree
Family Dollar
7-Eleven | 008163 | 7 eleven; seven eleven
Circle K
Sheetz
QuikTrip
Casey's
Speedway
RaceTrac
Love's
Pilot Flying J
Buc-ee's
Kwik Trip
Murphy USA
BJ's Wholesale | | bjs
CVS Pharmacy | CC0000 | cvs
Walgreens | E31837
Rite Aid
Shipt
Amazon Fresh
FreshDirect
Weee!
Thrive Market
Misfits Market
Imperfect Foods
Boxed
Sainsbury's
Asda
Morrisons
Waitrose
Ocado
Co-op
M&S Food
Loblaws
Sobeys
No Frills
FreshCo
Real Canadian Superstore
Woolworths
Coles
IGA
Carrefour
Auchan
E.Leclerc
Albert Heijn
Jumbo
Rewe
Edeka
Mercadona
Netto
Penny
Spar
Migros
""",
    "hk-food": """
Subway | 008C15
Chipotle | A81612
Chick-fil-A | E51636 | chickfila; chick fil a
Popeyes | F15A22
Panera Bread | 5A8C3E | panera
Panda Express | D02630
Wingstop | 016648
Raising Cane's | | canes
Zaxby's
Bojangles
Church's Texas Chicken
El Pollo Loco
Del Taco
Taco John's
Taco Bueno
Qdoba
Moe's Southwest Grill | | moes
Jersey Mike's
Jimmy John's
Firehouse Subs
Potbelly
Jason's Deli
McAlister's Deli
Schlotzsky's
Wawa
Cook Out
Golden Chick
Captain D's
Long John Silver's
Tropical Smoothie Cafe
Smoothie King
Jamba
Crumbl
Insomnia Cookies
Cinnabon
Auntie Anne's
Wetzel's Pretzels
Baskin-Robbins
Cold Stone Creamery
Marble Slab
Rita's Italian Ice
Yogurtland
Dairy Queen | EE3124
Applebee's
Chili's
Olive Garden
Denny's
IHOP
Cracker Barrel
Red Lobster
Outback Steakhouse
Texas Roadhouse
Buffalo Wild Wings
TGI Fridays
The Cheesecake Factory
LongHorn Steakhouse
Waffle House
Bob Evans
Perkins
First Watch
Huddle House
Golden Corral
Ruby Tuesday
O'Charley's
Hooters
Twin Peaks
BJ's Restaurant
Ruth's Chris
Benihana
P.F. Chang's
Chuck E. Cheese
Dave & Buster's
Main Event
Cava
Sweetgreen
Noodles & Company
Portillo's
Jollibee
Chowking
Greggs
Pret A Manger
Grubhub | F63440
Seamless
Caviar
Gopuff
Rappi
Talabat
Wolt
Lieferando
Menulog
SkipTheDishes
Waitr
Slice
ChowNow
Toast TakeOut
Olo
Favor
Blue Apron
Home Chef
Factor
Hungryroot
EveryPlate
Green Chef
Sunbasket
CookUnity
Marley Spoon
Dinnerly
OpenTable | DA3743
Resy
Tock
""",
    "hk-burger": """
Wendy's | E2203D | wendys
Five Guys | D21033
Shake Shack
In-N-Out Burger | E41E26 | innout; in n out
Whataburger | F26722
Culver's | 005696
Carl's Jr.
Hardee's
Jack in the Box
White Castle
Krystal
Checkers
Rally's
Steak 'n Shake
Freddy's
Smashburger
Sonic Drive-In | 0066B2 | sonic
Arby's | D2232A
Fatburger
The Habit Burger Grill | | habit
""",
    "hk-pizza": """
Domino's | 006491 | dominos
Pizza Hut | EE3A43 | pizzahut
Papa Johns | 007A53 | papa john's
Little Caesars | FF6600
Papa Murphy's
Marco's Pizza
MOD Pizza
Blaze Pizza
Hungry Howie's
Jet's Pizza
Cicis
Sbarro
Pizza Inn
Godfather's Pizza
Round Table Pizza
Mountain Mike's
Donatos
Toppers Pizza
""",
    "hk-coffee": """
Dunkin' | FF671F | dunkin; dunkin donuts
Tim Hortons | C8102E | tims
Dutch Bros | 0A4C8C
Caribou Coffee
Peet's Coffee
Biggby Coffee
Scooter's Coffee
Black Rifle Coffee
PJ's Coffee
Krispy Kreme
Costa Coffee
Caffe Nero
Philz Coffee
Blue Bottle
Nespresso
Keurig
""",
    "hk-car": """
Mercedes-Benz | | mercedes; mercedes me
Lexus
Dodge
Buick
GMC
Lincoln
Jaguar
Land Rover | | range rover
Alfa Romeo
Cupra
Rivian
Genesis
Scion
Pontiac
Saturn
Hummer
Fisker
VinFast
BYD
Geely
Tata Motors
Mahindra
Maruti Suzuki
Harley-Davidson
Yamaha Motor
Kawasaki
Indian Motorcycle
Carvana | 00AED9
CarMax | 003087
Autotrader
CarGurus
Cars.com
Kelley Blue Book | | kbb
Edmunds
Vroom
AutoNation
TrueCar
Copart
IAA | | iaai
CARFAX
Shift
Peddle
DriveTime
America's Car-Mart | | car mart
Lithia Driveway
Penske Automotive
EchoPark
Hendrick Automotive
Group 1 Automotive
Asbury Automotive
Byrider | | jd byrider
Westlake Financial
Credit Acceptance
Exeter Finance
Santander Consumer
Ally Auto
Capital One Auto
GM Financial
Ford Credit
Toyota Financial Services
Honda Financial Services
Nissan Motor Acceptance
Hyundai Motor Finance
Kia Finance
Enterprise Rent-A-Car | | enterprise
Hertz | FFD100
Avis
Budget
National Car Rental
Alamo
Sixt
Thrifty
Dollar Rent A Car
Fox Rent A Car
Payless Car Rental
Turo
Zipcar
Getaround
U-Haul
Penske Truck Rental
Jiffy Lube
Valvoline
Firestone
Pep Boys
AutoZone | D52B1E
O'Reilly Auto Parts
Advance Auto Parts
NAPA Auto Parts
Discount Tire
Tire Rack
Les Schwab
Midas
Meineke
Goodyear
Take 5 Oil Change
Mavis Tires
Christian Brothers Automotive
Safelite
Caliber Collision
OnStar
FordPass
myChevrolet
HondaLink
Hyundai Bluelink | | bluelink
Kia Connect
My BMW
Uconnect
NissanConnect
Subaru Starlink
Chevron
Exxon
Mobil
BP
Texaco
Valero
Marathon
Sunoco
Citgo
Phillips 66
Conoco
Gulf
ARCO
GasBuddy
Upside
E-ZPass | | ezpass
SunPass
FasTrak
TxTag
Peach Pass
I-PASS
NTTA TollTag
DMV
AAA
ParkMobile
SpotHero
PayByPhone
ParkWhiz
ChargePoint
Electrify America
EVgo
Blink Charging
""",
    "hk-tv": """
Hulu | 1CE783
Disney+ | 113CCF | disney plus; disneyplus
Peacock | | peacock tv
ESPN+ | | espn plus; espn
Sling TV | | sling
Philo
Pluto TV
Fandango at Home | | vudu
Discovery+ | | discovery plus
Criterion Channel
BritBox
CuriosityStream
Acorn TV
Shudder
AMC+
MGM+
Hallmark+
BET+
Frndly TV
DIRECTV
DIRECTV STREAM
Xfinity Stream
Cox Contour
DISH
Optimum TV
Fios TV
Crackle
Kanopy
Hoopla
Freevee
NOW TV
Sky Go
BBC iPlayer
ITVX
Channel 4
Stan
Binge
Foxtel
Disney+ Hotstar | | hotstar
JioCinema
ZEE5
SonyLIV
Viki
iQIYI
WeTV
Rakuten TV
Canal+
Videoland
Viaplay
NFL+
NFL Sunday Ticket
NBA League Pass
MLB.TV
NHL.TV
Fox Nation
Fox One
PBS Passport
YouTube Premium
Showmax
Hayu
HIDIVE
RetroCrush
""",
    "hk-music": """
SiriusXM | 0000EB | sirius xm
Amazon Music
Qobuz
Anghami
JioSaavn
Gaana
Boomplay
TuneIn
LiveOne
IDAGIO
Libby
Everand | | scribd
Storytel
Blinkist
Chirp
Libro.fm
Pocket FM
Wondery+
Podbean
Castbox
""",
    "hk-controller": """
Xbox | 107C10 | xbox live; xbox app
Xbox Game Pass | 107C10 | game pass
Nintendo | E60012 | nintendo account
Nintendo Switch Online | E60012 | switch online; nintendo eshop
Microsoft Rewards
Blizzard
Ubisoft Connect
GOG Galaxy
GeForce NOW
Logitech G | | logitech g hub
Overwolf
Green Man Gaming
Fanatical
G2A
Eneba
CDKeys
Instant Gaming
Kinguin
Amazon Luna | | luna
Prime Gaming
PlayStation Plus | | ps plus
PlayStation Network | | psn
EA Play
EA app
Rockstar Social Club | | social club
Mojang
Steam Deck
Google Play Games
Apple Arcade
Game Center
Meta Quest | | oculus
Viveport
Corsair iCUE
SteelSeries
HyperX
Alienware
MSI
ASUS ROG
Parsec
Shadow PC
Boosteroid
Xbox Cloud Gaming
IGN
GameFAQs
Tracker.gg
OP.GG
U.GG
Mobalytics
Blitz
Medal.tv | | medal
Outplayed
Nexus Mods
Thunderstore
GameBanana
NetEase Games | | netease
Tencent Games
Garena
Supercell ID | | supercell
Zynga
Moonton
Krafton
Nexon
NCSOFT
Capcom
Bandai Namco
CD PROJEKT RED
2K
Bungie
HoYoLAB | | hoyoverse
Jagex
Wargaming
Gaijin
Pearl Abyss
Smilegate
Kakao Games
Gameloft
Scopely
Playtika
Jam City
Hypixel
""",
    "hk-sword": """
Minecraft | 62B47A
Apex Legends | DA292A | apex
Overwatch 2 | F99E1A | overwatch
Call of Duty | | cod; warzone; black ops; modern warfare
Rocket League
Genshin Impact | | genshin
Honkai: Star Rail | | honkai; star rail
Zenless Zone Zero | | zzz
Wuthering Waves
World of Warcraft | | wow
Hearthstone
Diablo IV | | diablo; diablo 4
StarCraft II | | starcraft
Destiny 2 | | destiny
Halo
EA SPORTS FC | | ea fc
Madden NFL | | madden
NBA 2K
College Football 25 | | college football
The Sims 4 | | sims; the sims
GTA Online | | gta; gta v; grand theft auto
Red Dead Online | | red dead redemption
Elden Ring
Fallout 76 | | fallout
The Elder Scrolls Online | | eso; skyrim
Cyberpunk 2077
The Witcher 3 | | witcher
Among Us
Fall Guys
Pokemon GO
Pokemon TCG Live | | pokemon tcg
Pokemon Unite
Pokemon | | pokemon home
Mario Kart
Animal Crossing
The Legend of Zelda | | zelda
Super Smash Bros. | | smash bros
Splatoon 3 | | splatoon
Clash of Clans
Clash Royale
Brawl Stars
Hay Day
Boom Beach
Candy Crush
PUBG Mobile
Free Fire
Tetris
Terraria
Stardew Valley
DayZ
Escape from Tarkov | | tarkov
ARK: Survival Ascended | | ark
Warframe
RuneScape
Old School RuneScape | | osrs
Final Fantasy XIV | | ffxiv; final fantasy
EVE Online
Guild Wars 2
Lost Ark
New World
Marvel Rivals
Dead by Daylight
Rainbow Six Siege | | r6; siege; rainbow six
Splitgate
Paladins
SMITE 2 | | smite
Path of Exile 2 | | path of exile; poe
Baldur's Gate 3 | | baldurs gate
Helldivers 2
Palworld
Sea of Thieves
Deadlock
Team Fortress 2 | | tf2
Left 4 Dead 2
Naraka: Bladepoint | | naraka
Black Desert
Albion Online
MapleStory
Brawlhalla
MultiVersus
Call of Duty: Mobile | | cod mobile
Mobile Legends | | mlbb
Arena of Valor
Honor of Kings
Wild Rift
Teamfight Tactics | | tft
Legends of Runeterra
2XKO
Hytale
Valheim
Phasmophobia
Lethal Company
eFootball
Gran Turismo 7 | | gran turismo
Forza Horizon 5 | | forza
Need for Speed
The Crew Motorfest
Assassin's Creed
Far Cry
Battlefield
Titanfall 2
Mass Effect
Starfield
Monster Hunter Wilds | | monster hunter
Street Fighter 6 | | street fighter
Tekken 8 | | tekken
Mortal Kombat 1 | | mortal kombat
Geometry Dash
Subway Surfers
Monopoly GO!
Royal Match
8 Ball Pool
Neopets
Habbo
Second Life
VRChat
Rec Room
Beat Saber
Wordle
""",
    "hk-phone": """
T-Mobile | E20074 | tmobile
Mint Mobile | 2BAB7E | mint
Visible | 1D2AE6
Cricket Wireless | 00A651 | cricket
Metro by T-Mobile | 6E2C91 | metropcs
Tello
US Mobile
Google Fi | | fi
Consumer Cellular
Straight Talk
Total Wireless
Tracfone
Ting
Red Pocket
H2O Wireless
Ultra Mobile
Lycamobile
Simple Mobile
Page Plus
Twigby
Hello Mobile
Helium Mobile
Spectrum Mobile
Xfinity Mobile
Optimum Mobile
Good2Go Mobile
Walmart Family Mobile
UScellular
Assurance Wireless
SafeLink Wireless
Q Link Wireless
Life Wireless
giffgaff
EE
Three
O2
Sky Mobile
Lebara
VOXI
iD Mobile
Tesco Mobile
Fido
Koodo
Public Mobile
Freedom Mobile
Chatr
Lucky Mobile
Virgin Plus
Telcel
Movistar
Claro
Tigo
Jio
Airtel
Vi
Optus
Telstra
""",
    "hk-home": """
Xfinity | | comcast
Cox
Optimum
Frontier Internet | | frontier communications; frontier fiber
AT&T Fiber
Verizon Fios | | fios
Google Fiber
T-Mobile Home Internet
CenturyLink
Quantum Fiber
Kinetic by Windstream | | windstream
Mediacom
WOW!
Astound Broadband
Ziply Fiber
Metronet
Sparklight
altafiber
HughesNet
Viasat
EarthLink
Brightspeed
Breezeline
TDS Telecom
PG&E
Southern California Edison | | sce
SDG&E
Con Edison | | coned
Duke Energy
Dominion Energy
Georgia Power
FPL | | florida power and light
Xcel Energy
ComEd
PSE&G
National Grid
Eversource
Entergy
AEP
PPL Electric
DTE Energy
Consumers Energy
Ameren
Evergy
TXU Energy
Reliant
Direct Energy
Constellation
CenterPoint Energy
Atmos Energy
SoCalGas
Spire
Nicor Gas
American Water
Waste Management
Republic Services
Apartments.com
RentCafe
AppFolio
Buildium
Bilt Rewards
Avail
ADT
SimpliSafe
Google Nest | | nest
Realtor.com
Redfin
Trulia
Opendoor
Rocket Homes
""",
    "hk-shield": """
GEICO | 154BA2
Progressive | 0077C8
State Farm | E31837
Allstate | 0033A0
Liberty Mutual | 1A1446
Farmers Insurance
Nationwide Insurance
Travelers
American Family Insurance | | amfam
Erie Insurance
Root Insurance
Lemonade | FF0083
Clearcover
Dairyland
The General
Direct Auto Insurance
Mercury Insurance
Kemper
Safeco
Hippo
Branch Insurance
Openly
NEXT Insurance
Oscar Health
Ambetter
Blue Cross Blue Shield | | bcbs
Aetna
Cigna
UnitedHealthcare | | uhc
Humana
Kaiser Permanente | | kaiser
Anthem
Molina Healthcare
Medicare
Medicaid
HealthCare.gov
Delta Dental
VSP
EyeMed
MetLife
Prudential
Northwestern Mutual
New York Life
Guardian Life
Aflac
Policygenius
Haven Life
Ladder Life
Bestow
Chubb
Hagerty
Trupanion
Healthy Paws
Embrace Pet Insurance
ASPCA Pet Insurance
MyChart
Zocdoc
GoodRx
Teladoc
""",
}
