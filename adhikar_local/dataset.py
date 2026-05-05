"""
Adhikar-Aina | dataset.py

Generates 5,000 realistic Indian citizen profiles covering all major states,
with region-specific names, districts, caste distributions, and income patterns.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import List, Dict

# ── State-wise demographic data ───────────────────────────────────────────────

STATES: Dict[str, dict] = {
    "Uttar Pradesh": {
        "weight": 0.16,
        "districts": ["Lucknow","Varanasi","Allahabad","Agra","Kanpur","Meerut","Bareilly",
                       "Moradabad","Gorakhpur","Ghaziabad","Aligarh","Mathura","Jhansi","Saharanpur"],
        "male":    ["Ramesh","Suresh","Vikram","Rajesh","Manoj","Sanjay","Amit","Ravi","Deepak",
                    "Mukesh","Arun","Santosh","Arvind","Dinesh","Pramod","Satish","Vijay","Rajeev"],
        "female":  ["Sita","Geeta","Priya","Kavita","Sunita","Anita","Rekha","Usha","Meena",
                    "Radha","Pushpa","Shanti","Savitri","Urmila","Chandni","Laxmi","Kiran","Rani"],
        "surnames":["Sharma","Verma","Gupta","Yadav","Singh","Tiwari","Mishra","Pandey","Dubey",
                    "Prasad","Chauhan","Maurya","Patel","Rai","Srivastava","Kesarwani","Bajpai"],
        "caste":   {"SC":0.22,"ST":0.01,"OBC":0.43,"GEN":0.34},
        "occ":     {"farmer":0.50,"worker":0.22,"student":0.12,"entrepreneur":0.07,"unemployed":0.09},
        "income":  (25000, 600000),
    },
    "Maharashtra": {
        "weight": 0.085,
        "districts": ["Pune","Mumbai","Nashik","Nagpur","Kolhapur","Satara","Aurangabad",
                       "Solapur","Thane","Raigad","Jalgaon","Nanded","Latur","Amravati"],
        "male":    ["Rohan","Rahul","Nikhil","Arjun","Vivek","Sachin","Ajay","Mahesh","Prasad",
                    "Aditya","Sagar","Omkar","Tejas","Ganesh","Bharat","Sunil","Yogesh","Vaibhav"],
        "female":  ["Priya","Sneha","Pooja","Kavya","Diya","Meera","Shweta","Rujuta","Manasi",
                    "Vaishali","Aparna","Leela","Nandini","Supriya","Gauri","Jyoti","Madhuri"],
        "surnames":["Patil","Shinde","Jadhav","Pawar","Kulkarni","Deshmukh","More","Chavan","Kale",
                    "Joshi","Mhatre","Kadam","Sawant","Gaikwad","Bhosale","Salve","Thorat","Narke"],
        "caste":   {"SC":0.13,"ST":0.10,"OBC":0.44,"GEN":0.33},
        "occ":     {"farmer":0.34,"worker":0.26,"student":0.14,"entrepreneur":0.14,"unemployed":0.12},
        "income":  (40000, 1200000),
    },
    "Bihar": {
        "weight": 0.08,
        "districts": ["Patna","Gaya","Bhagalpur","Muzaffarpur","Darbhanga","Purnia","Nalanda",
                       "Ara","Begusarai","Saharsa","Hajipur","Sitamarhi","Madhubani","Jamui"],
        "male":    ["Rajan","Sunil","Pappu","Sanjit","Amar","Binod","Chetan","Dilip","Ganesh",
                    "Harishchandra","Jagdish","Kalyan","Lalan","Mithilesh","Naresh","Om","Pankaj"],
        "female":  ["Aarti","Babita","Chanda","Dolly","Fulwa","Gita","Hema","Indira","Jamuna",
                    "Kaveri","Lalita","Manju","Nandita","Poonam","Rekha","Sarita","Tulsi"],
        "surnames":["Kumar","Singh","Prasad","Mahto","Yadav","Sharma","Mandal","Das","Chamar",
                    "Pasi","Ravidas","Rajput","Thakur","Bhumihar","Koiri","Kurmi","Dusadh"],
        "caste":   {"SC":0.16,"ST":0.01,"OBC":0.52,"GEN":0.31},
        "occ":     {"farmer":0.55,"worker":0.20,"student":0.12,"entrepreneur":0.05,"unemployed":0.08},
        "income":  (20000, 450000),
    },
    "West Bengal": {
        "weight": 0.07,
        "districts": ["Kolkata","Howrah","Burdwan","Siliguri","Asansol","Durgapur","Malda",
                       "Cooch Behar","Murshidabad","Nadia","24 Parganas","Bankura","Purulia"],
        "male":    ["Biplab","Tanmoy","Sujit","Anirban","Debashis","Prodip","Sukanta","Soumen",
                    "Partha","Biman","Subir","Tapan","Rajat","Sandip","Ayan","Arnab","Subhasis"],
        "female":  ["Mitali","Piyali","Rupa","Soma","Tuli","Uma","Vandana","Aparna","Bula",
                    "Chaitali","Dipika","Ela","Fulki","Gargi","Hiya","Jharna","Karuna","Lata"],
        "surnames":["Chatterjee","Banerjee","Mukhopadhyay","Ghosh","Das","Bose","Sen","Roy",
                    "Biswas","Chakraborty","Datta","Ganguly","Haldar","Kundu","Mandal","Sarkar"],
        "caste":   {"SC":0.24,"ST":0.06,"OBC":0.32,"GEN":0.38},
        "occ":     {"farmer":0.38,"worker":0.28,"student":0.14,"entrepreneur":0.10,"unemployed":0.10},
        "income":  (30000, 700000),
    },
    "Madhya Pradesh": {
        "weight": 0.055,
        "districts": ["Bhopal","Indore","Jabalpur","Gwalior","Rewa","Satna","Ujjain","Sagar",
                       "Chhindwara","Ratlam","Dewas","Katni","Shivpuri","Balaghat","Tikamgarh"],
        "male":    ["Ramkumar","Shivprasad","Gopal","Laxminarayan","Balram","Chandrabhan","Dinkar",
                    "Feroz","Gaurishankar","Hemraj","Jagmohan","Kailash","Lalit","Mohanji"],
        "female":  ["Savita","Tara","Vimla","Yamuna","Archana","Beena","Chitra","Damini","Ekta",
                    "Falak","Ganga","Hansi","Indu","Jankee","Kanta","Lata","Mamta","Nidhi"],
        "surnames":["Tiwari","Shukla","Patel","Yadav","Jain","Gupta","Malviya","Raghuvanshi",
                    "Mishra","Pandey","Verma","Lodhi","Dhurve","Baiga","Gond","Bhil","Kurmi"],
        "caste":   {"SC":0.16,"ST":0.22,"OBC":0.42,"GEN":0.20},
        "occ":     {"farmer":0.52,"worker":0.18,"student":0.12,"entrepreneur":0.07,"unemployed":0.11},
        "income":  (22000, 550000),
    },
    "Rajasthan": {
        "weight": 0.055,
        "districts": ["Jaipur","Jodhpur","Udaipur","Kota","Bikaner","Ajmer","Alwar","Bhilwara",
                       "Sikar","Pali","Barmer","Jaisalmer","Chittorgarh","Tonk","Dungarpur"],
        "male":    ["Harish","Mohan","Narayan","Ramnaresh","Shyam","Tulsiram","Umesh","Veerendra",
                    "Wasim","Yashpal","Ajit","Baldev","Chandan","Dalchand","Eklavya","Fateh"],
        "female":  ["Hansa","Indra","Jyoti","Kamla","Leela","Mukta","Naina","Oomvati","Prabha",
                    "Quasar","Rekha","Sukhwanti","Tulika","Urmila","Varsha","Yasmin","Zara"],
        "surnames":["Sharma","Jat","Meena","Gujar","Rajput","Choudhary","Saini","Mali","Kumhar",
                    "Lohar","Suthar","Darji","Chamar","Bairwa","Nayak","Bhil","Mina","Gurjar"],
        "caste":   {"SC":0.18,"ST":0.14,"OBC":0.42,"GEN":0.26},
        "occ":     {"farmer":0.48,"worker":0.20,"student":0.13,"entrepreneur":0.09,"unemployed":0.10},
        "income":  (22000, 500000),
    },
    "Tamil Nadu": {
        "weight": 0.055,
        "districts": ["Chennai","Coimbatore","Madurai","Tiruchirappalli","Salem","Tirunelveli",
                       "Erode","Vellore","Thoothukudi","Thanjavur","Dindigul","Kanchipuram"],
        "male":    ["Murugan","Rajan","Selvam","Subramaniam","Krishnan","Venkat","Senthil","Arjun",
                    "Balan","Chandrasekhar","Durai","Elango","Ganesan","Hariharan","Ilavarasan"],
        "female":  ["Lakshmi","Meenakshi","Nirmala","Oviya","Pavithra","Revathi","Saranya",
                    "Thenmozhi","Uma","Vasantha","Abinaya","Bhuvana","Chitra","Deepa","Ezhilarasi"],
        "surnames":["Murugesan","Selvaraj","Krishnamurthy","Natarajan","Subramanian","Ramaswamy",
                    "Pillai","Rajan","Nadar","Gounder","Chettiar","Asari","Konar","Vellalar"],
        "caste":   {"SC":0.20,"ST":0.02,"OBC":0.51,"GEN":0.27},
        "occ":     {"farmer":0.35,"worker":0.30,"student":0.14,"entrepreneur":0.12,"unemployed":0.09},
        "income":  (35000, 900000),
    },
    "Karnataka": {
        "weight": 0.05,
        "districts": ["Bengaluru","Mysuru","Hubballi","Mangaluru","Belagavi","Kalaburagi","Davanagere",
                       "Shivamogga","Tumakuru","Raichur","Vijayapura","Dharwad","Hassan","Chitradurga"],
        "male":    ["Manjunath","Prakash","Girish","Suresh","Nagaraj","Ravi","Basavaraj","Chandrashekar",
                    "Deepak","Eranna","Fakirappa","Ganapathi","Hoovina","Imtiaz","Jayaprakash"],
        "female":  ["Kavitha","Lakshmi","Mamatha","Nagamma","Pushpa","Renuka","Shobha","Tara",
                    "Usha","Vani","Ambika","Bharathi","Chitra","Devika","Esha","Geeta","Hamsa"],
        "surnames":["Gowda","Reddy","Naik","Hegde","Rao","Murthy","Shetty","Kumar","Patil","Nayak",
                    "Vokkaliga","Lingayat","Kuruba","Bovi","Madiga","Holaya","Lambani"],
        "caste":   {"SC":0.18,"ST":0.07,"OBC":0.44,"GEN":0.31},
        "occ":     {"farmer":0.37,"worker":0.27,"student":0.15,"entrepreneur":0.12,"unemployed":0.09},
        "income":  (38000, 1000000),
    },
    "Gujarat": {
        "weight": 0.05,
        "districts": ["Ahmedabad","Surat","Vadodara","Rajkot","Bhavnagar","Jamnagar","Junagadh",
                       "Gandhinagar","Anand","Mehsana","Banaskantha","Patan","Sabarkantha"],
        "male":    ["Bhavesh","Chirag","Dhruv","Farukh","Gandabhai","Hitesh","Ilesh","Jayesh",
                    "Kalpesh","Lakhan","Mehul","Nilesh","Omkar","Prakash","Rajesh","Sandip"],
        "female":  ["Bhavna","Chetna","Drashti","Ekta","Falguni","Grishma","Hetal","Ila","Jinal",
                    "Kinjal","Lalita","Mansi","Nidhi","Pinki","Reena","Sapna","Taraben","Urvashi"],
        "surnames":["Patel","Shah","Mehta","Joshi","Desai","Parikh","Modi","Bhatt","Trivedi",
                    "Chaudhary","Solanki","Koli","Bariya","Vaghela","Thakor","Aahir","Rabari"],
        "caste":   {"SC":0.07,"ST":0.15,"OBC":0.42,"GEN":0.36},
        "occ":     {"farmer":0.30,"worker":0.25,"student":0.14,"entrepreneur":0.22,"unemployed":0.09},
        "income":  (40000, 1200000),
    },
    "Andhra Pradesh": {
        "weight": 0.04,
        "districts": ["Visakhapatnam","Vijayawada","Guntur","Nellore","Kurnool","Tirupati",
                       "Rajahmundry","Kakinada","Kadapa","Anantapur","Eluru","Ongole"],
        "male":    ["Ramaiah","Subbaiah","Naidu","Venkata","Srinivas","Ramamohan","Bhaskara",
                    "Chandra","Durga","Eswar","Gopal","Hari","Jagadeesh","Kiran","Lokesh"],
        "female":  ["Sarada","Tulasi","Usha","Vasundhara","Annapurna","Bhavani","Chandrika",
                    "Dhanalaxmi","Eswari","Gayatri","Himabindu","Indumathi","Janaki","Keerthi"],
        "surnames":["Reddy","Rao","Naidu","Varma","Raju","Choudary","Krishna","Sharma","Yadav",
                    "Kamma","Kapu","Balija","Mala","Madiga","Yanadi","Lambada","Boyi"],
        "caste":   {"SC":0.17,"ST":0.07,"OBC":0.47,"GEN":0.29},
        "occ":     {"farmer":0.42,"worker":0.25,"student":0.14,"entrepreneur":0.10,"unemployed":0.09},
        "income":  (30000, 750000),
    },
    "Telangana": {
        "weight": 0.03,
        "districts": ["Hyderabad","Warangal","Nizamabad","Karimnagar","Khammam","Nalgonda",
                       "Mahbubnagar","Adilabad","Siddipet","Sangareddy","Suryapet"],
        "male":    ["Mahender","Nagender","Praveen","Srinath","Venkateswarlu","Ashok","Bhaskar",
                    "Chandrashekar","Damodar","Eswar","Gaddam","Harikrishna","Ibrahim","Jagan"],
        "female":  ["Madhavi","Nandini","Padmavathi","Rajeswari","Sailaja","Tejaswini","Umarani",
                    "Vijayalaxmi","Aruna","Bindu","Chithra","Deepthi","Eswari","Farhat","Girija"],
        "surnames":["Reddy","Rao","Naik","Goud","Yadav","Padmashali","Mudiraj","Kuruma","Chakali",
                    "Madiga","Mala","Lambada","Koya","Gond","Chenchu","Bagata"],
        "caste":   {"SC":0.16,"ST":0.10,"OBC":0.46,"GEN":0.28},
        "occ":     {"farmer":0.38,"worker":0.27,"student":0.14,"entrepreneur":0.11,"unemployed":0.10},
        "income":  (32000, 800000),
    },
    "Kerala": {
        "weight": 0.025,
        "districts": ["Thiruvananthapuram","Kochi","Kozhikode","Thrissur","Kollam","Kannur",
                       "Palakkad","Malappuram","Alappuzha","Idukki","Kasaragod","Wayanad"],
        "male":    ["Rajan","Suresh","Binu","Cinoj","Dinu","Eldho","Fijil","Gireesh","Harikumar",
                    "Ijas","Jithin","Kiran","Lijo","Manu","Noble","Oommen","Pramod","Reji"],
        "female":  ["Asha","Bindhu","Chippy","Divya","Elsa","Fasila","Geetha","Hima","Indira",
                    "Jisha","Kanjana","Lekha","Meera","Nisha","Omana","Priya","Raji","Sreeja"],
        "surnames":["Nair","Pillai","Menon","Kurup","Nambiar","Thomas","Joseph","Mathew","George",
                    "Varghese","Namboothiri","Panicker","Ezhava","Namboodiri","Tharakan"],
        "caste":   {"SC":0.10,"ST":0.02,"OBC":0.32,"GEN":0.56},
        "occ":     {"farmer":0.22,"worker":0.32,"student":0.17,"entrepreneur":0.17,"unemployed":0.12},
        "income":  (45000, 1000000),
    },
    "Odisha": {
        "weight": 0.03,
        "districts": ["Bhubaneswar","Cuttack","Rourkela","Berhampur","Sambalpur","Balasore",
                       "Bhadrak","Baripada","Koraput","Rayagada","Bolangir","Dhenkanal"],
        "male":    ["Bibhuti","Chandan","Durga","Fanibhushan","Ganadev","Hemant","Iswar","Jaydev",
                    "Kartik","Laxmidhar","Mintu","Narayan","Prakash","Ramachandra","Surendra"],
        "female":  ["Annapurna","Basanti","Champa","Draupadi","Elina","Falgu","Gitanjali","Hema",
                    "Indira","Jamuna","Kumari","Laxmi","Mamata","Nalini","Parbati","Rekha"],
        "surnames":["Behera","Das","Nayak","Panda","Sahoo","Mohanty","Jena","Biswal","Parida",
                    "Pradhan","Sahu","Swain","Rout","Barik","Sethi","Tripathy","Gajapati"],
        "caste":   {"SC":0.17,"ST":0.23,"OBC":0.33,"GEN":0.27},
        "occ":     {"farmer":0.52,"worker":0.20,"student":0.12,"entrepreneur":0.06,"unemployed":0.10},
        "income":  (20000, 400000),
    },
    "Punjab": {
        "weight": 0.02,
        "districts": ["Amritsar","Ludhiana","Jalandhar","Patiala","Bathinda","Mohali","Gurdaspur",
                       "Hoshiarpur","Moga","Faridkot","Sangrur","Ropar"],
        "male":    ["Harpreet","Jasvir","Kulwant","Lakhwinder","Manpreet","Navdeep","Paramjit",
                    "Ranjit","Sarbjit","Tejinder","Amarjit","Balwinder","Charnjit","Daljit"],
        "female":  ["Gurpreet","Hardeep","Jaswinder","Kulwinder","Mandeep","Navneet","Parveen",
                    "Rajwinder","Simran","Taranjit","Amandeep","Baljinder","Charanjit","Diljit"],
        "surnames":["Singh","Kaur","Sidhu","Bains","Dhaliwal","Sandhu","Gill","Grewal","Bajwa",
                    "Virk","Cheema","Sekhon","Sohal","Randhawa","Kang","Atwal"],
        "caste":   {"SC":0.32,"ST":0.00,"OBC":0.30,"GEN":0.38},
        "occ":     {"farmer":0.35,"worker":0.27,"student":0.14,"entrepreneur":0.14,"unemployed":0.10},
        "income":  (45000, 900000),
    },
    "Assam": {
        "weight": 0.02,
        "districts": ["Guwahati","Dibrugarh","Silchar","Jorhat","Tezpur","Nagaon","Lakhimpur",
                       "Bongaigaon","Kamrup","Cachar","Dhubri","Goalpara","Barpeta"],
        "male":    ["Arup","Biren","Dilip","Emon","Fani","Gyanendra","Hemanta","Ishan","Jugal",
                    "Khagen","Lakhi","Mridul","Nikhil","Parag","Rituraj","Sanjib","Tapan"],
        "female":  ["Ankita","Barnali","Chayanika","Diptimala","Ema","Falguni","Gitali","Himangi",
                    "Indira","Jayashri","Kalpana","Lipika","Mitali","Namrata","Papori","Rekha"],
        "surnames":["Bora","Kalita","Das","Gogoi","Saikia","Baruah","Deka","Phukan","Hazarika",
                    "Nath","Borah","Konwar","Sonowal","Dutta","Bordoloi","Neog","Sharma"],
        "caste":   {"SC":0.07,"ST":0.13,"OBC":0.27,"GEN":0.53},
        "occ":     {"farmer":0.45,"worker":0.22,"student":0.14,"entrepreneur":0.09,"unemployed":0.10},
        "income":  (25000, 500000),
    },
    "Jharkhand": {
        "weight": 0.025,
        "districts": ["Ranchi","Dhanbad","Bokaro","Deoghar","Hazaribag","Jamshedpur","Giridih",
                       "Ramgarh","Koderma","Palamu","Gumla","Simdega","Khunti"],
        "male":    ["Anil","Birendra","Chandu","Dilip","Fagu","Ganga","Harish","Ivan","Janardan",
                    "Karan","Lal","Madan","Nandu","Pawan","Ratan","Sanjay","Tirkey"],
        "female":  ["Aarti","Bindu","Champa","Deepa","Elina","Fulwa","Gita","Hemlata","Indra",
                    "Jaya","Kamla","Laxmi","Mina","Nirmala","Priya","Rajni","Sunita"],
        "surnames":["Mahato","Singh","Kumar","Yadav","Sharma","Munda","Oraon","Santal","Birhor",
                    "Lodha","Kol","Paharia","Gond","Chero","Baiga","Asur"],
        "caste":   {"SC":0.12,"ST":0.28,"OBC":0.37,"GEN":0.23},
        "occ":     {"farmer":0.47,"worker":0.23,"student":0.12,"entrepreneur":0.06,"unemployed":0.12},
        "income":  (20000, 450000),
    },
}


def _w(pairs: list) -> str:
    return random.choices([v for v, _ in pairs], weights=[w for _, w in pairs], k=1)[0]


def _wdict(d: dict) -> str:
    keys = list(d.keys())
    wts  = list(d.values())
    return random.choices(keys, weights=wts, k=1)[0]


def _income_bracket(income: float) -> str:
    if income < 100_000: return "EWS"
    if income < 300_000: return "LIG"
    if income < 1_000_000: return "MIG"
    return "HIG"


def _land_category(acres: float) -> str:
    if acres < 1: return "marginal"
    if acres < 2: return "small"
    if acres < 5: return "medium"
    return "large"


def generate_citizen(index: int, state_name: str, sd: dict) -> dict:
    gender   = _w([("Male",0.52),("Female",0.48)])
    names    = sd["male"] if gender == "Male" else sd["female"]
    name     = f"{random.choice(names)} {random.choice(sd['surnames'])}"
    district = random.choice(sd["districts"])
    caste    = _wdict(sd["caste"])
    occ      = _wdict(sd["occ"])

    inc_min, inc_max = sd["income"]
    if occ == "farmer":
        income = round(random.triangular(inc_min, min(inc_max, 600_000), inc_min*3), -2)
        land   = round(random.uniform(0.1, 8.0), 2)
    elif occ == "entrepreneur":
        income = round(random.triangular(inc_min*2, inc_max, inc_max//2), -2)
        land   = round(random.uniform(0.0, 2.5), 2)
    elif occ == "student":
        income = round(random.uniform(0, min(inc_max*0.2, 200_000)), -2)
        land   = round(random.uniform(0.0, 0.5), 2)
    elif occ == "unemployed":
        income = round(random.uniform(0, min(inc_max*0.15, 150_000)), -2)
        land   = round(random.uniform(0.0, 0.3), 2)
    else:
        income = round(random.triangular(inc_min, min(inc_max, 700_000), inc_min*2), -2)
        land   = round(random.uniform(0.0, 1.0), 2)

    income = max(0, min(income, 3_000_000))
    age    = random.randint(18, 75)
    hhsize = random.randint(2, 8)
    bpl    = bool(income < 120_000 and hhsize >= 3) or income < 60_000
    children = age >= 22 and random.random() < 0.55
    girl     = children and random.random() < 0.47

    if bpl:
        housing = _w([("kutcha",0.48),("semi_pucca",0.38),("pucca",0.14)])
    else:
        housing = _w([("kutcha",0.10),("semi_pucca",0.34),("pucca",0.56)])

    emp_days = random.randint(0, 300)
    inc_bracket = _income_bracket(income)
    land_cat    = _land_category(land)

    tags = ",".join(filter(None,[
        occ,
        "low_income"  if income < 300_000 else "",
        "agriculture" if occ == "farmer"   else "",
        "education"   if occ == "student"  else "",
        "welfare"     if occ == "unemployed" else "",
        "girl_child"  if girl else "",
        caste.lower(),
        "tribal"      if caste == "ST" else "",
    ]))

    return {
        "citizen_id":          f"CIT-{index:05d}",
        "aadhar":              str(random.randint(200_000_000_000, 999_999_999_999)),
        "name":                name,
        "district":            district,
        "state":               state_name,
        "age":                 age,
        "gender":              gender,
        "caste_category":      caste,
        "annual_income":       float(income),
        "occupation":          occ,
        "land_acres":          float(land),
        "has_girl_child":      int(girl),
        "household_size":      hhsize,
        "has_bpl_card":        int(bpl),
        "housing_status":      housing,
        "employment_days":     emp_days,
        "income_bracket":      inc_bracket,
        "land_category":       land_cat,
        "occupation_category": occ,
        "citizen_tags":        tags,
        "created_at":          datetime.utcnow().isoformat(),
    }


def generate_all(n: int = 5000, seed: int = 42) -> List[dict]:
    """Generate n citizens proportionally distributed across Indian states."""
    random.seed(seed)

    state_names   = list(STATES.keys())
    state_weights = [STATES[s]["weight"] for s in state_names]

    # Normalise weights
    total = sum(state_weights)
    state_weights = [w / total for w in state_weights]

    citizens = []
    for i in range(1, n + 1):
        state_name = random.choices(state_names, weights=state_weights, k=1)[0]
        c = generate_citizen(i, state_name, STATES[state_name])
        citizens.append(c)

    # Pin a predictable test record as index 0
    citizens[0].update({
        "aadhar":          "999999999999",
        "name":            "Ramu Yadav",
        "state":           "Uttar Pradesh",
        "district":        "Varanasi",
        "occupation":      "farmer",
        "occupation_category": "farmer",
        "caste_category":  "OBC",
        "annual_income":   120000.0,
        "land_acres":      1.5,
        "income_bracket":  "LIG",
        "land_category":   "small",
        "has_bpl_card":    1,
        "citizen_tags":    "farmer,low_income,agriculture,obc",
    })
    return citizens
