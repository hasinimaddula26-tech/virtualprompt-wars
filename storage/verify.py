from election_assistant.data_sources import IndiaAdapter
a = IndiaAdapter()
r = a.list_regions()
print(f"Total regions: {len(r)}")
j = a.get_jurisdiction("tamil-nadu")
print(f"TN assembly seats: {j['contacts']['assembly_seats']}")
print(f"TN Lok Sabha seats: {j['contacts']['lok_sabha_seats']}")
print(f"Process steps: {len(j['process_steps'])}")
print(f"Step 1 help: {j['process_steps'][0]['help'][0]}")
print(f"CEO URL: {j['official']['elections_url']}")

j2 = a.get_jurisdiction("uttar-pradesh")
print(f"UP assembly seats: {j2['contacts']['assembly_seats']}")
print(f"UP Lok Sabha seats: {j2['contacts']['lok_sabha_seats']}")

j3 = a.get_jurisdiction("delhi")
print(f"Delhi type: {j3['contacts']['region_type']}")
print(f"Delhi assembly: {j3['contacts']['assembly_seats']}")
