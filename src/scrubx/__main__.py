"""CLI for ScrubX - 🧹 ScrubX makes your X/Twitter accounts squeaky-clean by erasing your entire post/likes history, bringing your account back to a blank slate.

Copyright (C) 2024  Parker Wahle

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import json
import logging
import webbrowser
from pathlib import Path
from typing import Iterator

import typer
from rich.logging import RichHandler
import tweepy

cli = typer.Typer()

CONSUMER_KEY = "3rJOl1ODzm9yZy63FACdg"
CONSUMER_SECRET = "5jPoQ5kQvMJFDYRNE8bQ4rHuds4xJqhvgNJM4awaE8"


def lazy_delete_tweets(client: tweepy.Client) -> Iterator[bool]:
    """
    Generator that lazily fetches and deletes tweets.
    Yields True for each successfully deleted tweet, False otherwise.
    """
    pagination_token = None
    while True:
        try:
            response = client.get_users_tweets(
                id=client.get_me().data.id,
                max_results=100,
                pagination_token=pagination_token
            )
            if not response.data:
                break
            for tweet in response.data:
                try:
                    client.delete_tweet(tweet.id)
                    yield True
                except tweepy.TweepyException as e:
                    logging.error(f"Error deleting tweet {tweet.id}: {e}")
                    yield False
            pagination_token = response.meta.get('next_token')
            if not pagination_token:
                break
        except tweepy.TweepyException as e:
            logging.error(f"Error fetching tweets: {e}")
            break


def get_user_tweet_count(client: tweepy.Client) -> int:
    """
    Fetch the number of tweets for the authenticated user.
    """
    try:
        user = client.get_me(user_fields=['public_metrics'])
        return user.data.public_metrics['tweet_count']
    except tweepy.TweepyException as e:
        logging.error(f"Error fetching user information: {e}")
        return 1000  # default


@cli.command()
def main() -> None:
    """Main function for ScrubX CLI."""
    # setup rich logger
    logging.basicConfig(handlers=[RichHandler()])
    logger = logging.getLogger("scrubx")

    # first step: see if we have json access_token and access_token_secret at ~/.scrubx.json
    oauth1_user_handler = tweepy.OAuth1UserHandler(
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        callback="oob"
    )

    try:
        with open(Path.home() / ".scrubx.json", "r") as file:
            data = json.load(file)
            access_token = data["access_token"]
            access_token_secret = data["access_token_secret"]
    except FileNotFoundError:
        typer.echo("You haven't signed in with Twitter yet. Opening signin page...")
        signin_url = oauth1_user_handler.get_authorization_url(signin_with_twitter=True)
        try:
            webbrowser.open(signin_url)
        except:
            pass
        typer.echo(f"Please sign in with Twitter at {signin_url} (tried to open)")
        pin = typer.prompt("Enter the PIN")
        access_token, access_token_secret = oauth1_user_handler.get_access_token(pin)
        with open(Path.home() / ".scrubx.json", "w") as file:
            json.dump(
                {"access_token": access_token, "access_token_secret": access_token_secret},
                file,
            )

    # set the tokens into the oauth
    oauth1_user_handler.set_access_token(access_token, access_token_secret)

    # create a twitter client
    client = tweepy.Client(
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    if not typer.confirm("Are you sure you want to delete all your tweets?"):
        typer.echo("Operation cancelled.")
        return

    total_deleted = 0
    max_tweets = get_user_tweet_count(client)
    with typer.progressbar(length=max_tweets, label="Deleting tweets") as progress:
        for success in lazy_delete_tweets(client):
            if success:
                total_deleted += 1
            progress.update(1)

    logger.info(f"Tweet deletion process completed. Total tweets deleted: {total_deleted}")


if __name__ == "__main__":  # pragma: no cover
    cli()

__all__ = ("cli",)
