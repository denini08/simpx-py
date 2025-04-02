import asyncio
import random
from profile import BotProfile
from bot import SimpleXBot
from extension import ChatWrapper

class AIResponseSimulator:
    """Simulates an AI response generation process."""
    
    @staticmethod
    async def generate_response(prompt: str) -> List[str]:
        """
        Simulate an AI generating a response incrementally.
        
        Args:
            prompt: The input prompt to generate a response for
        
        Returns:
            List of response chunks
        """
        # A dictionary of predefined responses for different prompts
        responses = {
            "tell me a story": [
                "Once upon a time,", 
                "in a magical land far away,", 
                "there lived a brave knight", 
                "who embarked on an incredible journey.", 
                "The knight's quest was to protect", 
                "the kingdom from an ancient dragon."
            ],
            "explain quantum physics": [
                "Quantum physics is a fundamental theory", 
                "that describes nature at the smallest scales", 
                "of energy levels of atoms and subatomic particles.", 
                "It introduces several mind-bending concepts", 
                "like quantum superposition and entanglement.", 
                "These phenomena challenge our classical understanding", 
                "of how the universe works."
            ],
            "default": [
                "Let me", 
                "generate", 
                "a response", 
                "for you", 
                "step by step."
            ]
        }
        
        # Choose the appropriate response list
        chunks = responses.get(prompt.lower(), responses["default"])
        
        return chunks
    
    @staticmethod
    async def generate_token_stream(prompt: str) -> List[str]:
        """
        Generate a response as individual word tokens.
        
        Args:
            prompt: The input prompt
        
        Returns:
            List of word tokens
        """
        # Simulating a more granular token-based generation
        tokens = prompt.split()
        
        # If no tokens, use a default
        if not tokens:
            tokens = ["Processing", "your", "request", "please", "wait"]
        
        return tokens

# Example usage
if __name__ == "__main__":
    
    # Create a bot profile
    profile = BotProfile(
        display_name="ExampleBot",
        full_name="Example Bot",
        description="An example bot using SimpX framework",
        welcome_message="Hello {name}! I'm an example bot. Try !help to see what I can do.",
        auto_accept_message="This is the example bot!",
        command_prefix="!"
    )
    
    # Create the bot with the profile
    bot = SimpleXBot(profile)
    
    @bot.command(name="info", help="Shows bot information")
    async def info_command(chat_info, profile):
        """Command that shows information about the bot's profile."""
        await bot.send_message(
            chat_info,
            f"*Bot Information*\n"
            f"Name: {profile.display_name}\n"
            f"Description: {profile.description}\n"
            f"Address: {profile.address}"
        )
    
    @bot.command(name="echo", help="Echoes your message")
    async def echo_command(chat_info, args):
        await bot.send_message(chat_info, f"You said: {args}")
        
    @bot.command(name="square", help="Calculates the square of a number")
    async def square_command(chat_info, args):
        try:
            number = float(args.strip())
            result = number * number
            await bot.send_message(chat_info, f"{number} × {number} = {result}")
        except ValueError:
            await bot.send_message(chat_info, "Please provide a valid number to square.")
    
    @bot.command(name="add", pattern=r"add (?P<a>\d+) (?P<b>\d+)", help="Adds two numbers")
    async def add_command(chat_info, a, b):
        result = int(a) + int(b)
        await bot.send_message(chat_info, f"{a} + {b} = {result}")
    
    @bot.command(name="ask", help="Ask an AI a question and get a live-streamed response")
    async def ask_command(chat_info, args):
        """
        Demonstrate live messaging with an AI-like response streaming.
        
        Args:
            chat_info: Chat information dictionary.
            args: User's prompt.
        """
        # Create a ChatWrapper instance using the provided chat_info and the bot's client
        chat = ChatWrapper(chat_info, bot.client)
        
        try:
            # Start a live message session with an initial text.
            initial_text = "🤖 Processing your request..."
            live_msg = await chat.send_message(initial_text, live=True, ttl=60)
            
            # Generate response chunks from the AI (simulate streaming)
            chunks = await AIResponseSimulator.generate_response(args)
            current_response = ""
            
            for chunk in chunks:
                current_response += f"{chunk} "
                # Update the live message with the current accumulated response.
                await live_msg.update_live(f"🔍 {current_response}")
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Finalize the live message by finishing it.
            await live_msg.finish_live()
        
        except Exception as e:
            # In case of error, finalize the live message with an error message.
            await live_msg.finish_live() 

    # Start the bot
    asyncio.run(bot.start())
