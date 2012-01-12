on run argv
    tell application "Spotify"
        play track item 1 of argv
    end tell
end run