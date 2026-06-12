import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
from database import get_db
from utils.location import get_nearby_profiles, calculate_distance

logger = logging.getLogger(__name__)

db = get_db()

# Store active profile viewing sessions
active_sessions = {}

async def view_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start viewing profiles based on user preference"""
    query = update.callback_query if update.callback_query else None
    user_id = update.effective_user.id if update.effective_user else update.message.from_user.id
    
    if query:
        await query.answer()
    
    # Check if user has profile
    my_profile = db.get_collection("profiles").find_one({"user_id": user_id})
    if not my_profile:
        msg = "❌ You need to create a profile first!\nUse /start to begin."
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return
    
    # Get user preference
    user = db.get_collection("users").find_one({"user_id": user_id})
    if not user or 'preference' not in user:
        keyboard = [[InlineKeyboardButton("⚙️ Set Preference", callback_data="set_preference")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = "⚠️ Please set your preference first!\n\nChoose who you want to see:"
        if query:
            await query.edit_message_text(msg, reply_markup=reply_markup)
        else:
            await update.message.reply_text(msg, reply_markup=reply_markup)
        return
    
    preference = user.get('preference', 'both')
    
    # Build query filter
    query_filter = {
        "user_id": {"$ne": user_id},
        "is_active": True
    }
    
    # Apply gender filter based on preference
    if preference == 'male':
        query_filter["gender"] = "male"
    elif preference == 'female':
        query_filter["gender"] = "female"
    # 'both' - show all genders
    
    # Get already liked users to exclude them
    liked_users = db.get_collection("likes").distinct("to_user", {"from_user": user_id})
    query_filter["user_id"] = {"$nin": liked_users + [user_id]}
    
    # Get profiles based on location or random
    profiles = []
    
    if my_profile.get('latitude') and my_profile.get('longitude'):
        # Get nearby profiles (within 50km)
        nearby = get_nearby_profiles(
            my_profile['latitude'],
            my_profile['longitude'],
            query_filter,
            max_distance_km=50
        )
        profiles = list(nearby)
        
        # Sort by distance
        for p in profiles:
            if p.get('latitude') and p.get('longitude'):
                p['distance'] = calculate_distance(
                    my_profile['latitude'], my_profile['longitude'],
                    p['latitude'], p['longitude']
                )
            else:
                p['distance'] = float('inf')
        profiles.sort(key=lambda x: x.get('distance', float('inf')))
    
    # If no nearby profiles, get random ones
    if not profiles:
        profiles = list(db.get_collection("profiles").find(query_filter).limit(100))
        # Shuffle for randomness
        import random
        random.shuffle(profiles)
    
    if not profiles:
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="view_profiles")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = "😔 **No profiles found!**\n\n"
        msg += "Possible reasons:\n"
        msg += "├ ─ No users matching your preference\n"
        msg += "├ ─ You've liked everyone available\n"
        msg += "└ ─ Try changing your preference\n\n"
        msg += "🔄 Click Refresh to check again."
        
        if query:
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # Store session
    active_sessions[user_id] = {
        'profiles': profiles,
        'current_index': 0,
        'preference': preference
    }
    
    # Show first profile
    await show_profile(update, context, user_id)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Display current profile to user"""
    session = active_sessions.get(user_id)
    if not session:
        return
    
    profiles = session['profiles']
    index = session['current_index']
    
    if index >= len(profiles):
        # No more profiles
        keyboard = [
            [InlineKeyboardButton("🔄 Start Over", callback_data="view_profiles")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = "🏁 **You've viewed all profiles!**\n\n"
        msg += "No more profiles available right now.\n"
        msg += "Come back later for new matches!"
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Clean up session
        del active_sessions[user_id]
        return
    
    profile = profiles[index]
    
    # Build profile display text
    text = f"👤 **{profile['name']}**\n"
    text += f"🎂 Age: {profile['age']}\n"
    text += f"📍 {profile.get('location_text', 'Location not specified')}\n"
    
    if profile.get('distance') and profile['distance'] != float('inf'):
        text += f"📏 Distance: {profile['distance']:.1f} km\n"
    
    if profile.get('about'):
        about_preview = profile['about'][:200]
        if len(profile['about']) > 200:
            about_preview += "..."
        text += f"\n📝 **About:**\n{about_preview}\n"
    
    text += f"\n👥 Profile {index + 1} of {len(profiles)}"
    
    # Build action buttons
    keyboard = [
        [
            InlineKeyboardButton("❤️ LIKE", callback_data=f"like_{profile['user_id']}"),
            InlineKeyboardButton("💬 CHAT", callback_data=f"chat_{profile['user_id']}")
        ],
        [
            InlineKeyboardButton("⏭️ SKIP", callback_data="skip_profile"),
            InlineKeyboardButton("🛑 STOP", callback_data="stop_viewing")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send media if available
    if profile.get('media') and len(profile['media']) > 0:
        # Try to send as media group first
        media_group = []
        for i, media_url in enumerate(profile['media'][:3]):
            if media_url.endswith(('jpg', 'jpeg', 'png', 'gif', 'webp')):
                media_group.append(InputMediaPhoto(media=media_url, caption=text if i == 0 else None))
            else:
                media_group.append(InputMediaVideo(media=media_url, caption=text if i == 0 else None))
        
        try:
            # Delete previous message if exists
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.delete_message()
            
            # Send media group
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.message.reply_media_group(media_group)
                await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown', disable_web_page_preview=True)
            else:
                await update.message.reply_media_group(media_group)
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown', disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Media group error: {e}")
            # Fallback to single message
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # No media, just text
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def like_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Like the current profile and move to next"""
    query = update.callback_query
    await query.answer("❤️ Liked! Moving to next profile...")
    
    user_id = update.effective_user.id
    target_id = int(query.data.split('_')[1])
    
    # Get target profile
    target_profile = db.get_collection("profiles").find_one({"user_id": target_id})
    if not target_profile:
        await query.edit_message_text("❌ Profile not found!")
        return
    
    # Check if already liked
    existing_like = db.get_collection("likes").find_one({
        "from_user": user_id,
        "to_user": target_id
    })
    
    if existing_like:
        await query.answer("You already liked this profile!", show_alert=True)
    else:
        # Create like record
        like_data = {
            "from_user": user_id,
            "to_user": target_id,
            "from_name": query.from_user.first_name,
            "to_name": target_profile.get('name'),
            "is_mutual": False,
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        db.get_collection("likes").insert_one(like_data)
        
        # Create notification for target
        notification = {
            "user_id": target_id,
            "type": "like",
            "from_user": user_id,
            "from_name": query.from_user.first_name,
            "message": f"{query.from_user.first_name} liked your profile!",
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        db.get_collection("notifications").insert_one(notification)
        
        # Check for mutual like (if target has also liked this user)
        mutual = db.get_collection("likes").find_one({
            "from_user": target_id,
            "to_user": user_id
        })
        
        if mutual:
            # Update both records as mutual
            db.get_collection("likes").update_many(
                {"$or": [
                    {"from_user": user_id, "to_user": target_id},
                    {"from_user": target_id, "to_user": user_id}
                ]},
                {"$set": {"is_mutual": True}}
            )
            
            # Send mutual match notification
            match_notification = {
                "user_id": target_id,
                "type": "mutual_match",
                "from_user": user_id,
                "from_name": query.from_user.first_name,
                "message": f"🎉 It's a match! You and {query.from_user.first_name} liked each other!",
                "is_read": False,
                "created_at": datetime.utcnow()
            }
            db.get_collection("notifications").insert_one(match_notification)
            
            match_notification2 = {
                "user_id": user_id,
                "type": "mutual_match",
                "from_user": target_id,
                "from_name": target_profile.get('name'),
                "message": f"🎉 It's a match! You and {target_profile.get('name')} liked each other!",
                "is_read": False,
                "created_at": datetime.utcnow()
            }
            db.get_collection("notifications").insert_one(match_notification2)
            
            await query.answer("🎉 It's a match! 🎉", show_alert=True)
    
    # Move to next profile
    session = active_sessions.get(user_id)
    if session:
        session['current_index'] += 1
        await show_profile(update, context, user_id)
    else:
        await view_profiles(update, context)

async def skip_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip current profile and move to next"""
    query = update.callback_query
    await query.answer("⏭️ Skipped")
    
    user_id = update.effective_user.id
    
    session = active_sessions.get(user_id)
    if session:
        session['current_index'] += 1
        await show_profile(update, context, user_id)
    else:
        await view_profiles(update, context)

async def stop_viewing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop viewing profiles and return to main menu"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Clean up session
    if user_id in active_sessions:
        del active_sessions[user_id]
    
    # Return to main menu
    from handlers.profile import show_main_menu
    await show_main_menu(update, context)

async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's own profile"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    profile = db.get_collection("profiles").find_one({"user_id": user_id})
    if not profile:
        await query.edit_message_text("❌ No profile found. Use /start to create one.")
        return
    
    # Get stats
    likes_received = db.get_collection("likes").count_documents({"to_user": user_id})
    
    # Build profile text
    text = f"👤 **YOUR PROFILE**\n\n"
    text += f"📛 Name: {profile['name']}\n"
    text += f"⚧ Gender: {'Male' if profile['gender'] == 'male' else 'Female'}\n"
    text += f"🎂 Age: {profile['age']}\n"
    text += f"📍 Location: {profile.get('location_text', 'Not set')}\n"
    text += f"❤️ Likes received: {likes_received}\n\n"
    
    if profile.get('about'):
        text += f"📝 **About:**\n{profile['about']}\n\n"
    
    text += f"📷 Media: {len(profile.get('media', []))} file(s)"
    
    # Action buttons
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send profile with media if available
    if profile.get('media') and len(profile['media']) > 0:
        media_group = []
        for i, media_url in enumerate(profile['media'][:3]):
            if media_url.endswith(('jpg', 'jpeg', 'png', 'gif', 'webp')):
                media_group.append(InputMediaPhoto(media=media_url, caption=text if i == 0 else None))
            else:
                media_group.append(InputMediaVideo(media=media_url, caption=text if i == 0 else None))
        
        try:
            await query.delete_message()
            await query.message.reply_media_group(media_group)
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Media error in my_profile: {e}")
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
