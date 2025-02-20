from trick_catalog import load_trick_catalog, process_trick

### Tests the trick catalog by inputting spin, flip, and body parameters, and getting back the result.

def get_numeric_input(prompt, multiple_of=None, allow_empty=True):
    """Helper function to get validated numeric input from user.
    
    Args:
        prompt (str): Input prompt to display
        multiple_of (int, optional): Number that input must be multiple of
        allow_empty (bool): Whether to allow empty input (defaults to 0)
    
    Returns:
        int: Validated numeric input
    """
    while True:
        try:
            user_input = input(prompt).strip()
            if not user_input and allow_empty:
                return 0
            value = int(user_input)
            if multiple_of and value % multiple_of != 0:
                print(f"Value must be a multiple of {multiple_of} degrees. Please try again.\n")
                continue
            return value
        except ValueError:
            print("Please enter a valid number.\n")

def test_trick():
    # Load the catalog
    catalog = load_trick_catalog("TrickCatalog.json")
    
    print("\n=== Test a Trick ===")
    # Get basic parameters
    natural = input("Natural Stance (G/r): ").upper()
    natural_stance = "Regular" if natural == "R" else "Goofy"
    
    stance_input = input("Active Stance (Enter for Normal, f/n/s for Fakie/Nollie/Switch): ").upper()
    stance = {
        "F": "Fakie",
        "N": "Nollie",
        "S": "Switch",
        "": "Normal"
    }.get(stance_input, "Normal")
    
    # Get trick parameters using the helper function
    spin = get_numeric_input("Board Spin (degrees, e.g. 180, Enter for 0): ", multiple_of=180)
    flip = get_numeric_input("Board Flip (degrees, e.g. 360, Enter for 0): ", multiple_of=360)
    body = get_numeric_input("Body Spin (degrees, Enter for 0): ", multiple_of=180)
    
    # Build input dictionary
    test_input = {
        "Spin": spin,
        "Flip": flip,
        "Body": body,
        "NaturalStance": natural_stance,
        "ActiveStance": stance
    }
    
    # Ask about late trick
    if input("\nAdd a late trick? (y/N): ").lower() == 'y':
        late_spin = get_numeric_input("Late Board Spin (Enter for 0): ", multiple_of=180)
        late_flip = get_numeric_input("Late Board Flip (Enter for 0): ", multiple_of=360)
        late_body = get_numeric_input("Late Body Spin (Enter for 0): ", multiple_of=180)

        test_input["LateParams"] = {
            "Spin": late_spin,
            "Flip": late_flip,
            "Body": late_body
        }
    
    # Process and print result
    result = process_trick(test_input, catalog)
    
    # If there's a late trick, append it to all other names
    if "LateParams" in test_input and "otherNames" in result:
        late_part = result["trickName"].split("Late")[-1]  # Get the "Late X" part
        result["otherNames"] = [f"{name} Late{late_part}" for name in result["otherNames"]]
    print("\n\n=== Result ===")
    print(f"\n{result['trickName']}:")
    print(f"Natural Stance: {natural_stance}")
    print(f"Active Stance: {stance}")
    print(f"Board Spin: {spin}°")
    print(f"Board Flip: {flip}°")
    print(f"Body Spin: {body}°")
    if "LateParams" in test_input:
        print(f"\n+ Late {result['lateTrickName']}:")
        print(f"Late Board Spin: {test_input['LateParams']['Spin']}°")
        print(f"Late Board Flip: {test_input['LateParams']['Flip']}°")
        print(f"Late Body Spin: {test_input['LateParams']['Body']}°")
    print("\nResult:", result)
        

if __name__ == "__main__":
    test_trick()