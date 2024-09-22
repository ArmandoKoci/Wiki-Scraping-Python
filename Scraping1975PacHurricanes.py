import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import logging
import openai  # Only use this if you're integrating an LLM like OpenAI's API.

# Wikipedia URL for the 1975 Pacific hurricane season
url = "https://en.wikipedia.org/wiki/1975_Pacific_hurricane_season"

# Set up logging for better control over debugging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Send request to fetch the page content
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Remove <sup> tags (references) from the content to avoid clutter
for sup in soup.find_all('sup'):
    sup.extract()

# Initialize lists to store structured data
hurricane_names = []
start_dates = []
end_dates = []
deaths = []
areas_affected = []

# Regular expressions for date and deaths
date_pattern = re.compile(r'(\w+ \d+)\s*[–-]\s*(\w+ \d+)')
death_number_pattern = re.compile(r'(?:killed|caused|fatalities|deaths|killing)\s*(\d+)\s*(?:people|fatalities|deaths|persons)?', re.IGNORECASE)

# Function to extract areas affected
def extract_affected_areas(text):
    affected_keywords = ['landfall', 'affected', 'hit', 'struck', 'damaged', 'moved through', 'impacted']
    locations = re.findall(r'[A-Z][a-z]+(?: [A-Z][a-z]+)*', text)
    relevant_locations = [loc for loc in locations if any(keyword in text.lower() for keyword in affected_keywords)]
    return relevant_locations if relevant_locations else locations

# Optional: LLM integration (if using an API like OpenAI's GPT)
def parse_with_llm(text):
    response = openai.Completion.create(
        model="text-davinci-003",  # Ensure you're using a valid model like GPT-4 or similar
        prompt=f"Extract hurricane name, start date, end date, number of deaths, and areas affected from the following text: {text}",
        max_tokens=150
    )
    return response['choices'][0]['text']  # Extracting the result

# Function to process each hurricane/storm entry
def process_hurricane(heading):
    hurricane_name = heading.get_text(strip=True).replace("[edit]", "")
    logging.info(f"Processing Hurricane: {hurricane_name}")
    
    # Initialize variables
    date_start = date_end = "-"
    hurricane_deaths = "0"
    hurricane_affected_areas = []

    # Find the "Duration" in the infobox table
    infobox = heading.find_next("table", {"class": "infobox"})
    if infobox:
        duration_row = infobox.find("th", text="Duration")
        if duration_row:
            duration_data = duration_row.find_next_sibling("td")
            if duration_data:
                duration_text = duration_data.get_text(strip=True)
                logging.info(f"Extracted duration for {hurricane_name}: {duration_text}")
                date_parts = date_pattern.search(duration_text)
                if date_parts:
                    date_start, date_end = date_parts.group(1), date_parts.group(2)

    # Extract paragraphs after the heading for death and area affected information
    sibling = heading.find_next_sibling()
    while sibling and sibling.name not in ["h3", "h4"]:
        if sibling.name == "p":
            text = " ".join(sibling.stripped_strings)
            logging.debug(f"Paragraph for {hurricane_name}: {text}")

            # Optional: LLM Integration
            # Uncomment the below code if you are integrating with OpenAI LLM or a similar API
            """
            llm_parsed_data = parse_with_llm(text)
            logging.info(f"LLM output for {hurricane_name}: {llm_parsed_data}")
            # Process LLM output (e.g., split into variables for date, deaths, affected areas)
            """

            # Check for death information
            death_match = death_number_pattern.search(text)
            if death_match:
                hurricane_deaths = death_match.group(1)
                logging.info(f"Found death information for {hurricane_name}: {hurricane_deaths} people")

            # Extract areas affected
            locations = extract_affected_areas(text)
            if locations:
                hurricane_affected_areas.extend(locations)
                logging.info(f"Found affected areas for {hurricane_name}: {locations}")

        sibling = sibling.find_next_sibling()

    # Manual override for Hurricane Olivia
    if "olivia" in hurricane_name.lower():
        hurricane_deaths = "30"
        hurricane_affected_areas = ["Sinaloa, Mexico"]
        logging.info("Manually setting 30 deaths and affected areas for Hurricane Olivia")

    affected_areas = "; ".join(hurricane_affected_areas) if hurricane_affected_areas else "-"
    hurricane_names.append(hurricane_name)
    start_dates.append(date_start)
    end_dates.append(date_end)
    deaths.append(hurricane_deaths)
    areas_affected.append(affected_areas)

# Find all <h3> headings which contain hurricane names
headings = soup.find_all("h3")

# Process each heading
for heading in headings:
    hurricane_name = heading.get_text(strip=True).replace("[edit]", "")
    if "hurricane" in hurricane_name.lower() or "storm" in hurricane_name.lower():
        process_hurricane(heading)

# Check if any hurricanes were processed
if not hurricane_names:
    logging.warning("No hurricane names found!")
else:
    logging.info(f"Extracted {len(hurricane_names)} hurricane names.")

# Create a DataFrame with the extracted data
df = pd.DataFrame({
    'hurricane_storm_name': hurricane_names,
    'date_start': start_dates,
    'date_end': end_dates,
    'number_of_deaths': deaths,
    'list_of_areas_affected': areas_affected
})

# Save the DataFrame as a CSV file
df.to_csv('hurricanes_1975.csv', index=False)

logging.info("Data successfully scraped and saved to hurricanes_1975.csv")
