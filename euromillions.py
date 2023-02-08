import json
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from email.mime.text import MIMEText
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

from data.samples import sample_euro_response
from dotenv import load_dotenv

load_dotenv()
EUROMILLIONS_API_KEY = os.getenv('EUROMILLIONS_API_KEY')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD')
GMAIL_SENDER = os.getenv('GMAIL_SENDER')
GMAIL_RECEIVER = os.getenv('GMAIL_RECEIVER')
BASE_DIR = Path(__file__).resolve().parent
env = Environment(
    loader=FileSystemLoader(f'{BASE_DIR}/templates'),
    autoescape=select_autoescape(['html', 'xml'])
)


@dataclass
class EuroGrille:
    numbers: list[int]
    stars: list[int]
    gains: Decimal = Decimal(0)


@dataclass
class EuroResult:
    numbers: list[int]
    stars: list[int]
    date: str
    winners_prize: dict


OUR_GRILLES = {
    "Amayas": EuroGrille(numbers=[9, 18, 34, 44, 45], stars=[9, 11]),
    "Hillal": EuroGrille(numbers=[8, 13, 22, 39, 42], stars=[2, 8]),
    "Tayeb1": EuroGrille(numbers=[1, 13, 17, 20, 45], stars=[3, 7]),
    "Tayeb2": EuroGrille(numbers=[1, 11, 12, 20, 21], stars=[5, 10]),
    "Yacine": EuroGrille(numbers=[13, 15, 21, 29, 40], stars=[5, 12]),
    "Moumen": EuroGrille(numbers=[2, 4, 7, 10, 20], stars=[1, 6]),
    "Khaled": EuroGrille(numbers=[6, 13, 21, 28, 48], stars=[3, 7]),
}


def get_last_result(mock=False) -> EuroResult:
    url = "https://euro-millions.p.rapidapi.com/results/lastresult"
    headers = {
        "X-RapidAPI-Key": EUROMILLIONS_API_KEY,
        "X-RapidAPI-Host": "euro-millions.p.rapidapi.com"
    }
    if mock:
        response = sample_euro_response
    else:
        response = requests.request("GET", url, headers=headers)
        response = json.loads(response.text)
    return EuroResult(
        numbers=response.get('numbers'),
        stars=response.get('stars'),
        date=response.get('date'),
        winners_prize=response.get('winners_prize')
    )


def check_matching_results(euro_result: EuroResult) -> dict[str, EuroGrille]:
    our_matching_results = {}
    for key, value in OUR_GRILLES.items():
        matching_numbers = [x for x in euro_result.numbers if x in OUR_GRILLES[key].numbers]
        matching_stars = [x for x in euro_result.stars if x in OUR_GRILLES[key].stars]
        our_matching_results[key] = EuroGrille(numbers=matching_numbers, stars=matching_stars)
    return our_matching_results


def set_gains(euro_result: EuroResult, our_matching_result: dict[str, EuroGrille]) -> None:
    for name, grille in our_matching_result.items():
        for key, value in euro_result.winners_prize.items():
            if int(value.get('win_numbers')) == len(grille.numbers) and int(value.get('win_stars')) == len(grille.stars):
                prize = value.get('prize').replace('.', '').replace(',', '.')
                OUR_GRILLES[name].gains = Decimal(prize)


def send_email(euro_result: EuroResult, our_matching_result: dict[str, EuroGrille], gains: Decimal) -> None:
    sender = GMAIL_SENDER
    receivers = GMAIL_RECEIVER
    password = GMAIL_PASSWORD

    msg = MIMEText(
        env.get_template('euromillions.html').render(
            euro_result=euro_result,
            our_grille=OUR_GRILLES,
            our_matching_result=our_matching_result,
            total_gains=gains),
        'html'
    )
    msg['Subject'] = f"Récapitulatif EuroMillions du {euro_result.date}"
    msg['From'] = sender
    msg['To'] = receivers
    smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtp_server.login(sender, password)
    smtp_server.sendmail(sender, receivers, msg.as_string())
    smtp_server.quit()


if __name__ == '__main__':
    print(f'Start Job => {datetime.now()}')
    last_euro_result = get_last_result(mock=True)
    print('Data fetched from api')
    matching_results = check_matching_results(last_euro_result)
    print('Metching results')
    set_gains(last_euro_result, matching_results)
    total_gains = sum([grille.gains for key, grille in OUR_GRILLES.items()])
    print('Sending mail')
    send_email(last_euro_result, matching_results, total_gains)
    print('Job Done!')
