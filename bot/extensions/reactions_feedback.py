def setup(bot):
    busy_emoji = getattr(bot, 'busy_emoji', '⌚')
    success_emoji = getattr(bot, 'success_emoji', '✅')
    error_emoji = getattr(bot, 'error_emoji', '❌')

    @bot.listen()
    async def on_command(ctx):
        await ctx.message.add_reaction(busy_emoji)

    @bot.listen()
    async def on_command_completion(ctx):
        await ctx.message.add_reaction(success_emoji)
        await ctx.message.remove_reaction(busy_emoji, ctx.bot.user)

    @bot.listen()
    async def on_command_error(ctx, error):
        await ctx.message.add_reaction(error_emoji)
        await ctx.message.remove_reaction(busy_emoji, ctx.bot.user)