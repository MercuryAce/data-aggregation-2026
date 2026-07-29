import re
from datetime import datetime
from models import db, Creator, Asset


def save_creators_for_markdown(markdown_text: str, coin_id: str, coin_name: str = None):
    """
    Parses the creator table from LunarCrush Markdown and saves
    creators + assets using the many-to-many relationship.
    """

    # Regex pattern for the Markdown table
    # Captures: handle, url_path, rank, followers, posts, engagements
    pattern = (
        r'\|\s*$$@?([^$$]+)\]\(([^)]+)\)\s*'
        r'\|\s*$$([^$$]*)\]\s*'
        r'\|\s*$$([^$$]*)\]\s*'
        r'\|\s*$$([^$$]*)\]\s*'
        r'\|\s*$$([^$$]*)\]\s*\|'
    )

    matches = re.findall(pattern, markdown_text)

    if not matches:
        print(f"No creators found in Markdown for {coin_id}")
        return

    # Get or create the Asset
    asset = Asset.query.filter_by(coin_id=coin_id).first()
    if not asset:
        asset = Asset(
            coin_id=coin_id,
            name=coin_name or coin_id.title()
        )
        db.session.add(asset)
        db.session.flush()

    new_creators = 0
    linked = 0

    for handle, url_path, rank, followers, posts, engagements in matches:
        handle = handle.strip()
        if not handle.startswith('@'):
            handle = '@' + handle

        # Determine platform and build full profile URL
        if '/tiktok/' in url_path:
            platform = 'tiktok'
            profile_url = f"https://www.tiktok.com{url_path.replace('/creator/tiktok', '')}"
        elif '/twitter/' in url_path:
            platform = 'twitter'
            profile_url = f"https://twitter.com{url_path.replace('/creator/twitter', '')}"
        else:
            platform = 'unknown'
            profile_url = url_path

        # Get or create Creator
        creator = Creator.query.filter_by(handle=handle).first()
        if not creator:
            creator = Creator(
                handle=handle,
                platform=platform,
                profile_url=profile_url,
                followers=followers.strip() if followers.strip() != '[--]' else None,
                posts=posts.strip() if posts.strip() != '[--]' else None,
                engagements=engagements.strip() if engagements.strip() != '[--]' else None,
            )
            db.session.add(creator)
            db.session.flush()
            new_creators += 1

        # Link creator to asset if not already linked
        if asset not in creator.assets:
            creator.assets.append(asset)
            linked += 1

            # Update stats if we have better data
            if followers.strip() and followers.strip() != '[--]':
                creator.followers = followers.strip()
            if posts.strip() and posts.strip() != '[--]':
                creator.posts = posts.strip()
            if engagements.strip() and engagements.strip() != '[--]':
                creator.engagements = engagements.strip()

            creator.updated_at = datetime.utcnow()

    db.session.commit()
    print(f"Saved {new_creators} new creators | Linked {linked} creators to {coin_id}")