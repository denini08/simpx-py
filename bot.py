import asyncio
import functools
import inspect
import re
from qr import print_qr_to_terminal
from typing import Dict, List, Callable, Optional, Any, Union, TypeVar, Pattern, Awaitable

from client import ChatClient, ChatCommandError
from command import ChatType
from response import ChatInfoType, ci_content_text, ChatResponse, ChatItem, ChatInfo, AChatItem

T = TypeVar('T')
CommandCallback = Callable[..., Awaitable[Any]]

class SimpleXBot:
    """
    A Pythonic framework for creating SimpleX chat bots.
    
    This class provides an easy-to-use interface for building bots using decorators
    similar to Discord.py, while respecting the SimpleX architecture.
    """
    
    def __init__(self, server_url: str = "ws://localhost:5225"):
        """
        Initialize the SimpleX bot.
        
        Args:
            server_url: The WebSocket URL of the SimpleX server
        """
        self.server_url = server_url
        self.client = None
        self.running = False
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._command_handlers: Dict[Union[str, Pattern], CommandCallback] = {}
        self._command_prefix = "!"
        self._help_command_enabled = True
        self._help_command_text = {}
        self._welcome_message = None

    async def start(self):
        """
        Start the bot and connect to the SimpleX server.
        
        This method initializes the ChatClient, checks for an active user profile,
        sets up the bot's address, and starts processing messages.
        """
        self.client = await ChatClient.create(self.server_url)
        
        # Get or create user profile
        user = await self.client.api_get_active_user()
        if not user:
            raise RuntimeError("No active user profile. Please create one using the terminal CLI first.")
        
        print(f"Bot profile: {user['profile']['displayName']} ({user['profile']['fullName']})")
        
        # Get or create the bot's address
        address = await self.client.api_get_user_address()
        if not address:
            address = await self.client.api_create_user_address()
        print(f"Bot address: {address}")

        print_qr_to_terminal(address)

        
        # Enable auto-accept for contacts
        await self.client.enable_address_auto_accept()
        
        # Register built-in help command if enabled
        if self._help_command_enabled:
            self._register_help_command()
        
        # Register default welcome message handler if one is set
        if self._welcome_message:
            self._register_welcome_handler()
        
        # Start processing messages
        self.running = True
        await self._process_messages()
    
    def _register_help_command(self):
        """Register the built-in help command."""
        async def help_command(chat_info, chat_item, **kwargs):
            command = kwargs.get('args', '').strip()
            if command:
                # Show help for specific command
                help_text = self._help_command_text.get(command)
                if help_text:
                    await self.send_message(chat_info, f"**{self._command_prefix}{command}**\n{help_text}")
                else:
                    await self.send_message(chat_info, f"No help available for command `{command}`")
            else:
                # Show general help
                commands = list(self._help_command_text.keys())
                if commands:
                    help_text = "Available commands:\n" + "\n".join(f"**{self._command_prefix}{cmd}** - {self._help_command_text[cmd].split('.')[0]}." for cmd in sorted(commands))
                    await self.send_message(chat_info, help_text)
                else:
                    await self.send_message(chat_info, "No commands available.")
        
        self.command("help", help="Shows this help message")(help_command)
    
    def _register_welcome_handler(self):
        """Register the default welcome message handler."""
        @self.event("contactConnected")
        async def on_contact_connected(response):
            contact = response.get("contact", {})
            display_name = contact.get("profile", {}).get("displayName", "Unknown")
            contact_id = contact.get("contactId")
            
            print(f"{display_name} connected")
            
            # Format the welcome message with the contact's display name
            message = self._welcome_message
            if "{name}" in message:
                message = message.format(name=display_name)
            
            # Send welcome message
            await self.client.api_send_text_message(
                ChatType.Direct,
                contact_id,
                message
            )
    
    async def _process_messages(self):
        """Process incoming messages and dispatch events."""
        while self.running:
            try:
                response = await self.client.msg_q.dequeue()
                await self._dispatch_event(response)
            except Exception as e:
                print(f"Error processing message: {e}")
    
    async def _dispatch_event(self, response: ChatResponse):
        """
        Dispatch an event based on the response type.
        
        Args:
            response: The chat response from the server
        """
        response_type = response.get("type")
        
        # Call registered event handlers for this response type
        handlers = self._event_handlers.get(response_type, [])
        for handler in handlers:
            try:
                await handler(response)
            except Exception as e:
                print(f"Error in event handler for {response_type}: {e}")
        
        # Special handling for new chat items (messages)
        if response_type == "newChatItems":
            await self._handle_new_chat_items(response)
    
    async def _handle_new_chat_items(self, response: ChatResponse):
        """
        Handle new chat items (messages).
        
        Args:
            response: The 'newChatItems' response
        """
        for chat_item_data in response.get("chatItems", []):
            chat_info = chat_item_data.get("chatInfo", {})
            chat_item = chat_item_data.get("chatItem", {})
            
            # Only process direct messages for now
            if chat_info.get("type") != "direct":
                continue
            
            # Get message content
            content = chat_item.get("content", {})
            msg_text = ci_content_text(content)
            if not msg_text:
                continue
            
            # Check if it's a command
            if msg_text.startswith(self._command_prefix):
                await self._handle_command(msg_text[len(self._command_prefix):], chat_info, chat_item)
    
    async def _handle_command(self, command_text: str, chat_info: ChatInfo, chat_item: ChatItem):
        """
        Handle a command message.
        
        Args:
            command_text: The command text without prefix
            chat_info: The chat info
            chat_item: The chat item containing the command
        """
        # Split the command into the command name and arguments
        parts = command_text.split(maxsplit=1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Check for exact command matches first
        if command_name in self._command_handlers:
            handler = self._command_handlers[command_name]
            await self._call_command_handler(handler, chat_info, chat_item, args=args)
            return
        
        # Then check for regex pattern matches
        for pattern, handler in self._command_handlers.items():
            if isinstance(pattern, Pattern) and pattern.match(command_text):
                match = pattern.match(command_text)
                if match:
                    kwargs = match.groupdict()
                    await self._call_command_handler(handler, chat_info, chat_item, **kwargs)
                    return
    
    async def _call_command_handler(self, handler: CommandCallback, chat_info: ChatInfo, chat_item: ChatItem, **kwargs):
        """
        Call a command handler with the appropriate arguments.
        
        This method inspects the handler's signature and passes only the
        parameters that it accepts.
        
        Args:
            handler: The command handler function
            chat_info: The chat info
            chat_item: The chat item
            **kwargs: Additional keyword arguments
        """
        try:
            sig = inspect.signature(handler)
            handler_kwargs = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                elif param_name == 'chat_info':
                    handler_kwargs['chat_info'] = chat_info
                elif param_name == 'chat_item':
                    handler_kwargs['chat_item'] = chat_item
                elif param_name == 'bot':
                    handler_kwargs['bot'] = self
                elif param_name == 'client':
                    handler_kwargs['client'] = self.client
                elif param_name in kwargs:
                    handler_kwargs[param_name] = kwargs[param_name]
                elif param.default is not inspect.Parameter.empty:
                    # If the parameter has a default value, we don't need to provide it
                    pass
                elif param.kind == inspect.Parameter.VAR_KEYWORD:
                    # If the handler accepts **kwargs, pass all remaining kwargs
                    handler_kwargs.update(kwargs)
            
            await handler(**handler_kwargs)
        except Exception as e:
            print(f"Error in command handler: {e}")
    
    async def send_message(self, chat_info: ChatInfo, text: str) -> List[AChatItem]:
        """
        Send a text message to a chat.
        
        Args:
            chat_info: The chat info
            text: The message text
            
        Returns:
            The list of chat items created
        """
        contact_id = chat_info.get("contact", {}).get("contactId")
        if not contact_id:
            raise ValueError("Cannot send message: invalid chat info")
        
        return await self.client.api_send_text_message(
            ChatType.Direct,
            contact_id,
            text
        )
    
    def set_command_prefix(self, prefix: str):
        """
        Set the command prefix.
        
        Args:
            prefix: The new command prefix
        """
        self._command_prefix = prefix
    
    def set_welcome_message(self, message: str):
        """
        Set a welcome message to send when a contact connects.
        
        You can use {name} in the message to include the contact's display name.
        
        Args:
            message: The welcome message template
        """
        self._welcome_message = message
    
    def on_contact_connected(self):
        """
        Decorator to register a custom handler for contact connections.
        This replaces the default welcome message handler.
        
        Returns:
            A decorator function
        """
        def decorator(func):
            if "contactConnected" in self._event_handlers:
                self._event_handlers["contactConnected"] = []
            return self.event("contactConnected")(func)
        return decorator
    
    def event(self, event_type: str = None):
        """
        Decorator to register an event handler.
        
        Args:
            event_type: The type of event to handle. If None, the function name is used.
            
        Returns:
            A decorator function
        """
        def decorator(func):
            nonlocal event_type
            if event_type is None:
                event_type = func.__name__
            
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            
            self._event_handlers[event_type].append(func)
            return func
        
        return decorator
    
    def command(self, name: str = None, *, pattern: str = None, help: str = None):
        """
        Decorator to register a command handler.
        
        Args:
            name: The name of the command
            pattern: A regex pattern to match against the command text
            help: Help text for the command
            
        Returns:
            A decorator function
        """
        def decorator(func):
            nonlocal name
            if name is None:
                name = func.__name__
            
            if pattern:
                compiled_pattern = re.compile(pattern)
                self._command_handlers[compiled_pattern] = func
            else:
                self._command_handlers[name] = func
            
            if help:
                self._help_command_text[name] = help
            
            return func
        
        return decorator
    
    def enable_help_command(self, enabled: bool = True):
        """
        Enable or disable the built-in help command.
        
        Args:
            enabled: Whether the help command should be enabled
        """
        self._help_command_enabled = enabled
    
    async def close(self):
        """Close the bot and disconnect from the SimpleX server."""
        if self.client:
            self.running = False
            await self.client.disconnect()


# Example usage
if __name__ == "__main__":
    bot = SimpleXBot()
    
    # Set a welcome message template
    bot.set_welcome_message("Hello {name}! I am a SimpleX bot created with the SimpX framework.")
    
    @bot.command(name="square", help="Calculates the square of a number")
    async def square_command(chat_info, args):
        try:
            number = float(args.strip())
            result = number * number
            await bot.send_message(chat_info, f"{number} × {number} = {result}")
        except ValueError:
            await bot.send_message(chat_info, "Please provide a valid number to square.")
    
    @bot.command(pattern=r"add (?P<a>\d+) (?P<b>\d+)", help="Adds two numbers")
    async def add_command(chat_info, a, b):
        result = int(a) + int(b)
        await bot.send_message(chat_info, f"{a} + {b} = {result}")
    
    asyncio.run(bot.start())
