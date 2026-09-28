"""Additional legitimate electronics catalogue rows for the SQLite store."""

from __future__ import annotations

CATALOGUE_PRODUCTS = [
    # Smartphones
    ("Apple", "iPhone 15", "Smartphones", "A reliable everyday smartphone with a sharp display and long software support.", 69999, 79900, 4.8, 1248, "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=800&q=80"),
    ("Samsung", "Galaxy S24", "Smartphones", "A compact Android flagship for photography, work, and entertainment.", 67999, 74999, 4.7, 968, "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=800&q=80"),
    ("OnePlus", "12", "Smartphones", "A fast flagship Android phone with a clean OxygenOS experience.", 59999, 64999, 4.6, 742, "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=80"),
    ("Google", "Pixel 8", "Smartphones", "A Google phone focused on camera quality and helpful software features.", 62999, 75999, 4.6, 581, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=800&q=80"),
    ("Xiaomi", "14", "Smartphones", "A compact flagship with a Leica-tuned camera system.", 54999, 69999, 4.5, 436, "https://images.unsplash.com/photo-1580910051074-3eb694886505?auto=format&fit=crop&w=800&q=80"),
    ("Motorola", "Edge 50 Pro", "Smartphones", "A well-built Android phone with a curved display and clean software.", 34999, 39999, 4.4, 312, "https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?auto=format&fit=crop&w=800&q=80"),
    # Laptops
    ("Samsung", "Galaxy Book4", "Laptops", "A lightweight laptop for work, study, and everyday browsing.", 62990, 72990, 4.6, 516, "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=800&q=80"),
    ("Dell", "Inspiron 14", "Laptops", "A dependable 14-inch laptop for documents, classes, and video calls.", 58990, 67990, 4.5, 428, "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?auto=format&fit=crop&w=800&q=80"),
    ("HP", "Pavilion 15", "Laptops", "A 15-inch Windows laptop suited to study, browsing, and light creative work.", 61990, 71990, 4.5, 603, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80"),
    ("Lenovo", "IdeaPad Slim 5", "Laptops", "A slim everyday laptop with a comfortable keyboard and long battery life.", 57990, 66990, 4.6, 487, "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?auto=format&fit=crop&w=800&q=80"),
    ("ASUS", "Vivobook 15", "Laptops", "A practical laptop for students and professionals who need a clear display.", 54990, 64990, 4.5, 394, "https://images.unsplash.com/photo-1484788984921-03950022c9ef?auto=format&fit=crop&w=800&q=80"),
    ("Acer", "Aspire 5", "Laptops", "An affordable Windows laptop for browsing, documents, and online classes.", 47990, 55990, 4.4, 351, "https://images.unsplash.com/photo-1587614387466-0e11b6c898f2?auto=format&fit=crop&w=800&q=80"),
    ("Apple", "MacBook Air 13 M3", "Laptops", "A quiet, lightweight notebook for writing, study, and everyday creative work.", 114900, 124900, 4.8, 812, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80"),
    # Headphones / audio
    ("Sony", "WH-1000XM5", "Headphones", "Wireless over-ear headphones with strong noise cancelling.", 29990, 34990, 4.7, 892, "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=800&q=80"),
    ("Bose", "QuietComfort Ultra", "Headphones", "Comfortable wireless headphones designed for quiet travel and focused work.", 35900, 39900, 4.8, 264, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80"),
    ("JBL", "Tune 770NC", "Headphones", "Everyday wireless headphones with active noise cancelling and long battery life.", 7999, 9999, 4.4, 518, "https://images.unsplash.com/photo-1484704849700-f032a5071ee6?auto=format&fit=crop&w=800&q=80"),
    ("Sennheiser", "Accentum Plus", "Headphones", "Wireless headphones with a balanced sound profile for music and calls.", 19990, 24990, 4.6, 187, "https://images.unsplash.com/photo-1487215078519-e21cc028cb29?auto=format&fit=crop&w=800&q=80"),
    ("Apple", "AirPods Pro 2", "Headphones", "In-ear wireless earphones with adaptive noise cancelling and spatial audio.", 22900, 26900, 4.7, 1104, "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?auto=format&fit=crop&w=800&q=80"),
    # Smartwatches
    ("Apple", "Watch Series 9", "Smart Watches", "A smartwatch for activity tracking, notifications, and everyday health checks.", 39900, 44900, 4.8, 674, "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?auto=format&fit=crop&w=800&q=80"),
    ("Samsung", "Galaxy Watch 6", "Smart Watches", "An Android smartwatch with fitness tracking and a bright circular display.", 28990, 34990, 4.6, 421, "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"),
    ("Garmin", "Venu 3", "Smart Watches", "A GPS fitness watch with detailed health metrics and long battery life.", 44990, 49990, 4.7, 239, "https://images.unsplash.com/photo-1579586337273-1d02baabb8c2?auto=format&fit=crop&w=800&q=80"),
    ("Amazfit", "GTR 4", "Smart Watches", "A lightweight smartwatch with GPS and multi-day battery life.", 15999, 18999, 4.4, 306, "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=800&q=80"),
    ("OnePlus", "Watch 2", "Smart Watches", "A Wear OS smartwatch with fast charging and familiar Android apps.", 24999, 27999, 4.5, 198, "https://images.unsplash.com/photo-1522312346375-d1a52e2b99b3?auto=format&fit=crop&w=800&q=80"),
    # Cameras
    ("Canon", "EOS R50", "Cameras", "An accessible mirrorless camera for photos and 4K video.", 62995, 72995, 4.6, 291, "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=800&q=80"),
    ("Nikon", "Z30", "Cameras", "A compact mirrorless camera aimed at vlogging and still photography.", 67995, 76995, 4.5, 174, "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?auto=format&fit=crop&w=800&q=80"),
    ("Sony", "ZV-E10", "Cameras", "A vlogging camera with a vari-angle screen and interchangeable lenses.", 69990, 79990, 4.6, 256, "https://images.unsplash.com/photo-1606986628025-35d57ab27324?auto=format&fit=crop&w=800&q=80"),
    ("Fujifilm", "X-S20", "Cameras", "A versatile mirrorless camera with film-inspired colour profiles.", 119999, 134999, 4.7, 142, "https://images.unsplash.com/photo-1495707903480-898bd09d25b4?auto=format&fit=crop&w=800&q=80"),
    ("Panasonic", "Lumix G100", "Cameras", "A lightweight Micro Four Thirds camera for video creators.", 54990, 64990, 4.4, 118, "https://images.unsplash.com/photo-1616423640778-28d1b53229bd?auto=format&fit=crop&w=800&q=80"),
    # Tablets
    ("Apple", "iPad 10th Generation", "Tablets", "A colourful tablet for notes, streaming, and everyday apps.", 44900, 49900, 4.7, 733, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=800&q=80"),
    ("Samsung", "Galaxy Tab S9 FE", "Tablets", "An Android tablet with a vivid display for study and entertainment.", 36999, 42999, 4.6, 412, "https://images.unsplash.com/photo-1561154464-82e9adf32764?auto=format&fit=crop&w=800&q=80"),
    ("Lenovo", "Tab P12", "Tablets", "A large Android tablet suited to reading, video, and light productivity.", 32999, 37999, 4.4, 221, "https://images.unsplash.com/photo-1585784378140-7c5d1b0b1b1b?auto=format&fit=crop&w=800&q=80"),
    ("OnePlus", "Pad 2", "Tablets", "A fast Android tablet with a wide display for media and note-taking.", 39999, 44999, 4.5, 167, "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=80"),
    ("Xiaomi", "Pad 6", "Tablets", "A high-refresh Android tablet for entertainment and casual work.", 26999, 31999, 4.5, 389, "https://images.unsplash.com/photo-1587033411394-4b0d3d6d4a4b?auto=format&fit=crop&w=800&q=80"),
    # Computer peripherals
    ("Logitech", "MX Master 3S", "Computer Peripherals", "A precision wireless mouse for long editing and office sessions.", 9995, 12495, 4.8, 954, "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=800&q=80"),
    ("Keychron", "K2 Mechanical Keyboard", "Computer Peripherals", "A compact wireless mechanical keyboard for typing and programming.", 8990, 10990, 4.6, 410, "https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?auto=format&fit=crop&w=800&q=80"),
    ("LG", "27UP850 4K Monitor", "Computer Peripherals", "A 27-inch 4K USB-C monitor for design, documents, and video.", 34990, 42990, 4.6, 287, "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=800&q=80"),
    ("WD", "My Passport 2TB", "Computer Peripherals", "A portable hard drive for backups and extra file storage.", 5999, 7499, 4.5, 1203, "https://images.unsplash.com/photo-1531492741700-0d3d2d0c0c0c?auto=format&fit=crop&w=800&q=80"),
    ("Anker", "USB-C Hub 7-in-1", "Computer Peripherals", "A compact hub that adds HDMI, USB-A, and card-reader ports to a laptop.", 3999, 4999, 4.5, 644, "https://images.unsplash.com/photo-1625948515291-69613efd103f?auto=format&fit=crop&w=800&q=80"),
    # Computer components
    ("AMD", "Ryzen 5 7600", "Computer Components", "A six-core desktop processor for gaming and everyday productivity.", 18990, 22990, 4.7, 318, "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?auto=format&fit=crop&w=800&q=80"),
    ("NVIDIA", "GeForce RTX 4060", "Computer Components", "A graphics card for 1080p and 1440p gaming with modern upscaling.", 32990, 37990, 4.6, 502, "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?auto=format&fit=crop&w=800&q=80"),
    ("Corsair", "Vengeance 32GB DDR5", "Computer Components", "A 32 GB DDR5 memory kit for smooth multitasking.", 10990, 13490, 4.7, 276, "https://images.unsplash.com/photo-1562976540-1502c2145186?auto=format&fit=crop&w=800&q=80"),
    ("Samsung", "990 EVO 1TB NVMe SSD", "Computer Components", "A 1 TB NVMe SSD for faster boot times and application loading.", 7999, 9999, 4.8, 641, "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?auto=format&fit=crop&w=800&q=80"),
    ("Cooler Master", "MWE Gold 750W", "Computer Components", "A 750W 80 Plus Gold power supply for a mid-range desktop build.", 8990, 10990, 4.5, 193, "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?auto=format&fit=crop&w=800&q=80"),
    # Desktops
    ("Dell", "Inspiron Desktop", "Desktops", "A compact desktop tower for home office work and study.", 54990, 62990, 4.4, 164, "https://images.unsplash.com/photo-1587831990711-23ca6442bcf8?auto=format&fit=crop&w=800&q=80"),
    ("HP", "Pavilion Desktop", "Desktops", "A ready-to-use desktop PC for browsing, documents, and media.", 52990, 59990, 4.4, 148, "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?auto=format&fit=crop&w=800&q=80"),
    ("Lenovo", "IdeaCentre 5", "Desktops", "A family desktop with room for storage upgrades.", 49990, 57990, 4.3, 121, "https://images.unsplash.com/photo-1587202372616-b43abea06c2a?auto=format&fit=crop&w=800&q=80"),
    ("Apple", "Mac mini M2", "Desktops", "A small desktop computer for a quiet home or office setup.", 59900, 69900, 4.8, 390, "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?auto=format&fit=crop&w=800&q=80"),
    ("ASUS", "ExpertCenter D7", "Desktops", "A business desktop designed for reliable everyday computing.", 46990, 53990, 4.3, 97, "https://images.unsplash.com/photo-1593640495253-23196b27a87f?auto=format&fit=crop&w=800&q=80"),
    # Telephones
    ("Panasonic", "KX-TGF382 Cordless Phone", "Telephones", "A cordless home phone with an answering machine and backup handset.", 6490, 7990, 4.4, 215, "https://images.unsplash.com/photo-1520923642038-b4259acecbd7?auto=format&fit=crop&w=800&q=80"),
    ("Gigaset", "A540 Duo", "Telephones", "A DECT cordless telephone set for clear home calls.", 4990, 5990, 4.3, 132, "https://images.unsplash.com/photo-1557180295-76eee20ae8aa?auto=format&fit=crop&w=800&q=80"),
    ("Cisco", "IP Phone 8841", "Telephones", "A business desk phone with a colour screen and wired handset.", 18990, 21990, 4.5, 88, "https://images.unsplash.com/photo-1516387938699-a93567ec168e?auto=format&fit=crop&w=800&q=80"),
    ("VTech", "CS6719 Cordless Phone", "Telephones", "A simple cordless phone with caller ID for home use.", 3990, 4990, 4.2, 176, "https://images.unsplash.com/photo-1584433144859-1fc3ab64a957?auto=format&fit=crop&w=800&q=80"),
    ("Yealink", "T46U IP Phone", "Telephones", "An office IP phone with programmable keys and HD audio.", 14990, 17990, 4.6, 74, "https://images.unsplash.com/photo-1563013544-824ae1b704d3?auto=format&fit=crop&w=800&q=80"),
    # Video / TV
    ("Samsung", "Crystal UHD 43-inch", "Video", "A 43-inch 4K smart TV for everyday streaming.", 32990, 39990, 4.5, 802, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=800&q=80"),
    ("LG", "OLED 48 C3", "Video", "A 48-inch OLED TV with deep contrast for films and games.", 89990, 109990, 4.8, 367, "https://images.unsplash.com/photo-1461151304267-38535e780c79?auto=format&fit=crop&w=800&q=80"),
    ("Sony", "Bravia 55 X75L", "Video", "A 55-inch 4K Google TV with clear motion for sports and movies.", 72990, 84990, 4.6, 294, "https://images.unsplash.com/photo-1593784991095-a205069470b6?auto=format&fit=crop&w=800&q=80"),
    ("TCL", "P755 50-inch", "Video", "An affordable 50-inch 4K Google TV for living-room streaming.", 36990, 44990, 4.4, 441, "https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?auto=format&fit=crop&w=800&q=80"),
    ("Xiaomi", "Smart TV X 43", "Video", "A 43-inch 4K Android TV with a simple smart interface.", 24990, 29990, 4.3, 688, "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=800&q=80"),
    # Other electronics
    ("Amazon", "Kindle Paperwhite", "Other electronics", "A glare-free e-reader for books and long reading sessions.", 14999, 16999, 4.7, 2150, "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=800&q=80"),
    ("GoPro", "HERO12 Black", "Other electronics", "An action camera for travel, sport, and waterproof video.", 37990, 44990, 4.6, 534, "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?auto=format&fit=crop&w=800&q=80"),
    ("DJI", "Mini 4K Drone", "Other electronics", "A lightweight camera drone for aerial photos and video.", 42990, 49990, 4.6, 201, "https://images.unsplash.com/photo-1473968512647-3e447244af8f?auto=format&fit=crop&w=800&q=80"),
    ("Kindle", "Fire 7 Tablet", "Other electronics", "A compact entertainment tablet for reading, video, and apps.", 9999, 12999, 4.3, 890, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=800&q=80"),
    ("Anker", "737 Power Bank", "Other electronics", "A high-capacity USB-C power bank for phones and laptops.", 12999, 14999, 4.7, 763, "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?auto=format&fit=crop&w=800&q=80"),
    ("Raspberry Pi", "5 Starter Kit", "Other electronics", "A compact single-board computer kit for learning and hobby projects.", 8990, 10990, 4.8, 412, "https://images.unsplash.com/photo-1553406830-ef2513450d76?auto=format&fit=crop&w=800&q=80"),
]
