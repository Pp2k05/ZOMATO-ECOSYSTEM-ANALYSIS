from PIL import Image, ImageDraw, ImageFont
import textwrap

def create_slide(width=1080, height=1350, bg_color="#000000"):
    return Image.new("RGB", (width, height), bg_color)

def draw_text_centered(draw, text, font, y_pos, color="#FFFFFF", width=1080):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    x_pos = (width - w) / 2
    draw.text((x_pos, y_pos), text, font=font, fill=color)
    return bbox[3] - bbox[1] # return height of text

def generate_carousel():
    slides = []
    
    try:
        # Try to load a bold modern font, fallback to default Arial if not available
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 90)
            font_title_large = ImageFont.truetype("arialbd.ttf", 130)
            font_sub = ImageFont.truetype("arial.ttf", 60)
            font_huge = ImageFont.truetype("arialbd.ttf", 160)
        except:
            # Absolute fallback
            font_title = ImageFont.load_default()
            font_title_large = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            font_huge = ImageFont.load_default()
    except Exception as e:
        print("Font error:", e)
        return

    # Slide 1: Hook
    s1 = create_slide()
    d1 = ImageDraw.Draw(s1)
    draw_text_centered(d1, "Is Zomato", font_title_large, 450, "#FFFFFF")
    draw_text_centered(d1, "cracking under", font_title_large, 600, "#FFFFFF")
    draw_text_centered(d1, "scale?", font_title_large, 750, "#FF9500")
    d1.line([(340, 950), (740, 950)], fill="#FF9500", width=5)
    slides.append(s1)

    # Slide 2: The Data
    s2 = create_slide()
    d2 = ImageDraw.Draw(s2)
    draw_text_centered(d2, "We stopped guessing.", font_title, 400, "#FFFFFF")
    draw_text_centered(d2, "And scraped", font_title, 550, "#FFFFFF")
    draw_text_centered(d2, "55,000", font_huge, 700, "#FF9500")
    draw_text_centered(d2, "Verified Reviews.", font_title, 900, "#FFFFFF")
    slides.append(s2)

    # Slide 3: AntiGravity
    s3 = create_slide()
    d3 = ImageDraw.Draw(s3)
    draw_text_centered(d3, "Powered by", font_title, 500, "#FFFFFF")
    draw_text_centered(d3, "ANTIGRAVITY", font_huge, 650, "#FF9500")
    d3.line([(340, 850), (740, 850)], fill="#FF9500", width=5)
    draw_text_centered(d3, "Zero Paid APIs.", font_sub, 950, "#FFFFFF")
    slides.append(s3)

    # Slide 4: Scope
    s4 = create_slide()
    d4 = ImageDraw.Draw(s4)
    draw_text_centered(d4, "The Ecosystem:", font_title, 400, "#FFFFFF")
    draw_text_centered(d4, "Zomato", font_title_large, 600, "#FF9500")
    draw_text_centered(d4, "Blinkit", font_title_large, 750, "#FF9500")
    draw_text_centered(d4, "District", font_title_large, 900, "#FF9500")
    slides.append(s4)

    # Slide 5: NLP Engine
    s5 = create_slide()
    d5 = ImageDraw.Draw(s5)
    draw_text_centered(d5, "We built an", font_title, 400, "#FFFFFF")
    draw_text_centered(d5, "Enterprise NLP", font_title_large, 550, "#FF9500")
    draw_text_centered(d5, "Engine.", font_title_large, 700, "#FF9500")
    draw_text_centered(d5, "Categorizing raw sentiment", font_sub, 900, "#FFFFFF")
    draw_text_centered(d5, "into 6 VoC Pillars.", font_sub, 1000, "#FFFFFF")
    slides.append(s5)

    # Slide 6: Accuracy
    s6 = create_slide()
    d6 = ImageDraw.Draw(s6)
    draw_text_centered(d6, "Accuracy Rate:", font_title_large, 500, "#FFFFFF")
    draw_text_centered(d6, "~85%", font_huge, 680, "#FF9500")
    d6.line([(340, 900), (740, 900)], fill="#FF9500", width=5)
    draw_text_centered(d6, "No LLM required.", font_sub, 1000, "#FFFFFF")
    slides.append(s6)

    # Slide 7: Next steps
    s7 = create_slide()
    d7 = ImageDraw.Draw(s7)
    draw_text_centered(d7, "Data is primed.", font_title_large, 400, "#FFFFFF")
    draw_text_centered(d7, "Next up:", font_title, 600, "#FFFFFF")
    draw_text_centered(d7, "SQL & Power BI", font_title_large, 750, "#FF9500")
    slides.append(s7)

    # Slide 8: CTA
    s8 = create_slide()
    d8 = ImageDraw.Draw(s8)
    draw_text_centered(d8, "The final reports", font_title_large, 450, "#FFFFFF")
    draw_text_centered(d8, "are dropping", font_title_large, 600, "#FFFFFF")
    draw_text_centered(d8, "SOON.", font_huge, 750, "#FF9500")
    d8.line([(340, 980), (740, 980)], fill="#FF9500", width=5)
    slides.append(s8)

    # Slide 9: Question
    s9 = create_slide()
    d9 = ImageDraw.Draw(s9)
    draw_text_centered(d9, "Which app should", font_title, 450, "#FF9500")
    draw_text_centered(d9, "we expose first?", font_title_large, 600, "#FF9500")
    draw_text_centered(d9, "Comment below.", font_sub, 800, "#FFFFFF")
    slides.append(s9)

    # Save to PDF
    slides[0].save(
        "LinkedIn_Carousel_Zomato.pdf", 
        save_all=True, 
        append_images=slides[1:], 
        resolution=100.0
    )
    print("Carousel saved to LinkedIn_Carousel_Zomato.pdf")

if __name__ == "__main__":
    generate_carousel()
