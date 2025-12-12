"""
Fun Cog
Handles fun and utility commands including ping, 8ball, and car facts.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)


class Fun(commands.Cog):
    """Fun and utility commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # 8ball responses
        self.eight_ball_responses = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful."
        ]
        
        # Car facts database
        self.car_facts = [
            "The first car was invented in 1886 by Karl Benz. It was called the Benz Patent-Motorwagen.",
            "The world's fastest production car is the SSC Tuatara, which reached 331 mph in 2020.",
            "The Ford Model T was the first mass-produced car, with over 15 million units sold between 1908 and 1927.",
            "The average car has over 30,000 parts, counting every single component.",
            "The first speeding ticket was issued in 1902 to a driver going 45 mph in a 20 mph zone.",
            "The Bugatti Veyron costs more than $1 million and can burn through a full tank of gas in just 12 minutes at top speed.",
            "The first car radio was invented in 1929 by Paul Galvin, founder of Motorola.",
            "The world's longest traffic jam occurred in China in 2010, stretching 62 miles and lasting 12 days.",
            "The first car accident happened in 1891 in Ohio, when a car hit a tree root and crashed.",
            "The average American spends about 38 hours per year stuck in traffic.",
            "The first production car with air conditioning was the 1940 Packard.",
            "The Toyota Corolla is the best-selling car of all time, with over 50 million units sold worldwide.",
            "The first car to break the sound barrier was the ThrustSSC in 1997, reaching 763 mph.",
            "The average car weighs about 4,000 pounds, but the lightest production car (the Peel P50) weighs only 130 pounds.",
            "The first car with a V8 engine was the 1914 Cadillac Type 51.",
            "The world's most expensive car ever sold was a 1962 Ferrari 250 GTO, which sold for $48.4 million in 2018.",
            "The first car with power steering was the 1951 Chrysler Imperial.",
            "The average car has about 3,000 feet of electrical wiring inside it.",
            "The first car to use seat belts was the 1959 Volvo Amazon.",
            "The world's largest car manufacturer is Toyota, producing over 10 million vehicles per year.",
            "The first car with an automatic transmission was the 1939 Oldsmobile.",
            "The average car can travel about 300 miles on a full tank of gas.",
            "The first car with airbags was the 1973 Oldsmobile Toronado.",
            "The world's smallest production car is the Peel P50, which is only 54 inches long.",
            "The first car to use disc brakes was the 1953 Jaguar C-Type.",
            "The average car produces about 4.6 metric tons of CO2 per year.",
            "The first car with GPS navigation was the 1995 Oldsmobile 88.",
            "The world's most fuel-efficient car is the Volkswagen XL1, achieving 261 mpg.",
            "The first car with cruise control was the 1958 Chrysler Imperial.",
            "The average car has about 30,000 miles of wear on its tires before they need replacement."
        ]
    
    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        """Check the bot's latency."""
        latency_ms = round(self.bot.latency * 1000, 2)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Bot latency: **{latency_ms}ms**",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        # Add a fun status based on latency
        if latency_ms < 100:
            status = "Excellent connection! ⚡"
        elif latency_ms < 200:
            status = "Good connection! ✅"
        elif latency_ms < 300:
            status = "Moderate connection ⚠️"
        else:
            status = "Slow connection 🐌"
        
        embed.add_field(name="Status", value=status, inline=False)
        embed.set_footer(text="GearShift Bot")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    @app_commands.describe(question="Your question for the 8-ball")
    async def eight_ball(
        self,
        interaction: discord.Interaction,
        question: str
    ):
        """Ask the magic 8-ball a question."""
        if not question.endswith('?'):
            question = question + '?'
        
        response = random.choice(self.eight_ball_responses)
        
        # Determine color based on response type
        if any(word in response.lower() for word in ['yes', 'certain', 'definitely', 'good', 'likely', 'rely']):
            color = discord.Color.green()
        elif any(word in response.lower() for word in ['no', 'doubtful', 'count on it']):
            color = discord.Color.red()
        else:
            color = discord.Color.orange()
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=response, inline=False)
        embed.set_footer(text="GearShift Bot")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="carfacts", description="Get a random interesting car fact")
    async def car_facts(self, interaction: discord.Interaction):
        """Get a random car fact."""
        fact = random.choice(self.car_facts)
        
        embed = discord.Embed(
            title="🚗 Car Fact",
            description=fact,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="GearShift Bot | Connecting Car Culture")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(Fun(bot))

