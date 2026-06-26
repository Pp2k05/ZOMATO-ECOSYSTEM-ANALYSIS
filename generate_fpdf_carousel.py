from fpdf import FPDF

class CarouselPDF(FPDF):
    def __init__(self):
        # 108mm x 135mm is a 4:5 ratio, perfect for LinkedIn
        super().__init__(orientation="P", unit="mm", format=(108, 135))
        self.set_auto_page_break(auto=False)
        
    def add_slide(self):
        self.add_page()
        # Set background to black
        self.set_fill_color(0, 0, 0)
        self.rect(0, 0, 108, 135, 'F')
        
    def draw_text_centered(self, text, y_pos, font_family='helvetica', style='B', size=24, r=255, g=255, b=255):
        self.set_font(font_family, style, size)
        self.set_text_color(r, g, b)
        self.set_xy(0, y_pos)
        self.cell(w=108, h=10, text=text, border=0, align='C')
        
    def draw_line(self, y_pos):
        self.set_draw_color(255, 149, 0) # Orange
        self.set_line_width(1)
        self.line(30, y_pos, 78, y_pos)

def generate():
    pdf = CarouselPDF()
    
    # Slide 1: Philosophical Hook
    pdf.add_slide()
    pdf.draw_text_centered("Every App You Use", 45, size=26)
    pdf.draw_text_centered("Runs on a Loop.", 60, size=32, r=255, g=149, b=0)
    pdf.draw_line(80)
    pdf.draw_text_centered("And it learns from you.", 90, size=16, style="")
    
    # Slide 2: The Data
    pdf.add_slide()
    pdf.draw_text_centered("I wanted to", 40, size=24)
    pdf.draw_text_centered("see it in action.", 55, size=24)
    pdf.draw_text_centered("So I scraped", 75, size=18, style="")
    pdf.draw_text_centered("55,000", 90, size=40, r=255, g=149, b=0)
    pdf.draw_text_centered("Verified Reviews.", 110, size=18)
    
    # Slide 3: Scope
    pdf.add_slide()
    pdf.draw_text_centered("Food Tech &", 40, size=24)
    pdf.draw_text_centered("Q-Commerce Data.", 55, size=24)
    pdf.draw_line(75)
    pdf.draw_text_centered("Zomato | Blinkit | District", 90, size=20, r=255, g=149, b=0)
    
    # Slide 4: AntiGravity
    pdf.add_slide()
    pdf.draw_text_centered("Powered by", 50, size=20)
    pdf.draw_text_centered("ANTIGRAVITY", 65, size=32, r=255, g=184, b=0)
    pdf.draw_line(85)
    pdf.draw_text_centered("Zero Paid APIs.", 95, size=16, style="")
    
    # Slide 5: NLP Engine
    pdf.add_slide()
    pdf.draw_text_centered("I built an", 40, size=20)
    pdf.draw_text_centered("Enterprise NLP", 55, size=28, r=255, g=149, b=0)
    pdf.draw_text_centered("Engine.", 70, size=28, r=255, g=149, b=0)
    pdf.draw_text_centered("Categorizing chaos", 90, size=14, style="")
    pdf.draw_text_centered("into 6 Enterprise Pillars.", 100, size=14, style="")
    
    # Slide 6: Accuracy
    pdf.add_slide()
    pdf.draw_text_centered("Accuracy Rate:", 50, size=24)
    pdf.draw_text_centered("~85%", 70, size=40, r=255, g=149, b=0)
    pdf.draw_line(90)
    pdf.draw_text_centered("Rule-Based Heuristics.", 100, size=14, style="")
    
    # Slide 7: Next steps
    pdf.add_slide()
    pdf.draw_text_centered("Data is primed.", 40, size=24)
    pdf.draw_text_centered("Next up:", 60, size=20)
    pdf.draw_text_centered("SQL & Power BI", 75, size=28, r=255, g=149, b=0)
    
    # Slide 8: CTA
    pdf.add_slide()
    pdf.draw_text_centered("The real insights", 45, size=24)
    pdf.draw_text_centered("drop tomorrow.", 60, size=24)
    pdf.draw_text_centered("STAY TUNED.", 80, size=36, r=255, g=149, b=0)
    pdf.draw_line(100)
    
    pdf.output("LinkedIn_Carousel_Antigravity.pdf")
    print("Vector PDF saved to LinkedIn_Carousel_Antigravity.pdf")

if __name__ == "__main__":
    generate()
