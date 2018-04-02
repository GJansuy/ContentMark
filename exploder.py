import sys
import os.path
import pickle
import re

class Exploder:
    def __init__(self, target=None, template=None):
        if target is None:
            sys.exit("The target is invalid! " + str(target))
            return
        if not os.path.isfile(target):
            sys.exit("The target doesn't exist!")
            return

        if template is None:
            template = "default_page.html"
        if not os.path.isfile(template):
            sys.exit("Template doesn't exist!!")
            return

        # Make a dictionary to contain the state
        cache = {}
        cache["target"] = target
        with open(target, "r") as f:
            cache["input"] = f.read().splitlines()
        if len(cache["input"]) < 1:
            sys.exit("There doesn't seem to be anything here.")
        
        self.breakdown(cache)
        self.organize(cache)
        self.pagify(cache, template)
        # Export solid block
        with open(target+".out","w") as f:
            for line in cache["output"]:
                f.write(line)
                f.write("\n")


    def classify(self, elements=None, extras=None):
        if extras != None:
            if elements == None:
                elements = []
            elements.append(extras)
        elif elements == None:
            return ""
        return " class=\""+(" ".join(elements))+"\""

    def breakdown(self, cache):
        cache["output"] = []
        
        # Mode  :: 0 Single line, 1X for Auto wrap, 2 for Table
        #       :: 11 Unordered List wrap, 12 Ordered List wrap,
        #       :: 15 Box Note
        mode = [0]
        indent_level = 2
        indent_storage = indent_level
        indent_change = 0
        table_caption_found = False

        for line in cache["input"]:
            if len(line.strip()) < 1:
                continue # Ignore empty lines
            #print(line)

            buf = ""
            indent_change = 0

            if "|}" in line.strip():
                mode.pop()
                cache["output"].append(("  "*(indent_level-1))+"</tr>")
                indent_level = indent_storage
                table_caption_found = False
                buf = "</table></div>"
            
            elif mode[-1] == 2:
                extras = ""
                content = line.lstrip()
                if "|+" in content and not table_caption_found:
                    buf = "<caption>"+ content.lstrip("|+") +"</caption>"
                    table_caption_found = True
                elif "!" in content[0]:
                    if "!" in content[1:]:
                        extras, content = content[1:].split("!",1)
                        extras = " " + extras 
                    buf = "<th"+ extras +">" + content.rstrip().lstrip("!") +"</th>"
                elif content.rstrip() in "|-":
                    indent_level -= 1
                    cache["output"].append(("  "*indent_level)+ "</tr>")
                    cache["output"].append(("  "*indent_level)+ "<tr>")
                    buf = ""
                    indent_level += 1
                elif "|" in content[0]:
                    if "|" in content[1:]:
                        extras,content = content[1:].split("|",1)
                        extras = " " +extras
                    # Kind of blows away any specific formatting of spacing
                    # But this should work for now. Using multiple sub()'s
                    # With gradually decreasing search counts would allow for
                    # finer control though.
                    content = re.sub("^(\s{2,}","&emsp;",content)
                    buf = "<td" + extras + ">"+content.lstrip("|")+"</td>"

            elif "{|" in line.strip():
                mode.append(2)
                indent_storage = indent_level
                extras = []
                if len(line.strip()) > 2 :
                    extras.append(line.split("{|")[1].strip())
                cache["output"].append(("  "*indent_level)+ "<div" + self.classify(elements=extras,extras="table-wrapper")+"><table>")
                indent_level += 2
                #TODO: Implement Wikimedia class extensions
            
            elif "-" in line.lstrip()[0]: # Operator Found
                operator, content = line.split(">",1)
                elements = None
                #print("Operator:",operator, "Length:",len(operator))
                if "," in operator:
                    operator, elements = operator.split(",",1)
                    if "," in elements:
                        elements = elements.split(",")
                    else:
                        elements = [elements]

                #print("Elements:",elements)

                if "-H" in operator:
                    # Headings
                    level = 1
                    if len(operator) >2:
                        level = int(operator[2])
                    buf ="<h"+ str(level) + self.classify(elements=elements)+ ">"
                    buf += content 
                    buf += "</h"+str(level)+">"

                elif "-Q" in operator:
                    # Quote+Author
                    if "-QA" in operator:
                        buf = "  <span"+self.classify(elements=elements,extras="quote-author")+">"
                        buf += content + "</span>"
                        buf += "\n"+("  "*indent_level)+ "</div>"
                    else:
                        buf = "<div class=\"well well-sm\">\n"+ ("  "*(indent_level+1))+"<span"
                        buf += self.classify(elements=elements,extras="quote")
                        buf += ">" + content + "</span>"

                elif "-B" in operator:
                    # BN, BNA, BNE
                    if "-BNA" in operator:
                        if mode[-1] == 15:
                            buf = "  <div"+ self.classify(elements=elements,extras="box-note-author")+">" + content + "</div>\n"+("  "*(indent_level-1))+"</div>"
                            indent_level -= 1
                            mode.pop()
                        elif mode[-1] == 0:
                            continue

                    elif "-BNE" in operator:
                        if mode[-1] == 15:
                            buf = "</div>"
                            indent_level -=1
                            mode.pop()
                        elif mode[-1] == 0:
                            continue
                    elif "-BN" in operator:
                        buf = "<div"+ self.classify(elements=elements,extras="box-note")+">"
                        indent_change += 1
                        mode.append(15)

                elif "-L" in operator:
                    # (Unordered) Lists Begins/Ends
                    if "-LB" in operator:
                        buf = "<ul"+ self.classify(elements=elements) +">"
                        indent_change += 1
                        mode.append(11)

                    elif "-LE" in operator:
                        buf = "</ul>"
                        indent_level -= 1
                        mode.pop()

                elif "-OL" in operator: 
                    # Ordered List Begins/Ends
                    if "-OLB" in operator:
                        buf = "<ol"+ self.classify(elements=elements) +">"
                        indent_change += 1
                        mode.append(12)

                    elif "-OLE" in operator:
                        buf = "</ol>"
                        indent_change -= 1
                        mode.pop()
            elif "<br" in line.strip()[:3]:
                buf = line

            # Check for HTML comments
            elif "<!--" in line.lstrip()[:4]:
                buf = line # Skips the length condition in mode 0/15
            
            elif "<" in line.lstrip()[0] and ">" in line.rstrip()[-1]:
                buf = line # Line appears to be straight HTML
                print("Bypass line found: " + line)

            if mode[-1] == 0 or mode[-1] == 15: # Plain mode
                if len(buf) < 1:
                    buf = "<p>"+line+"</p>"
            elif mode[-1] == 11 or mode[-1] == 12: # [O]LB
                if len(buf) < 1:
                    if ":" in line:
                        buf = line.split(":", 1)
                        buf = ("<b>"+buf[0]+" :</b>"+ buf[1])
                        buf = "<li>" + buf  + "</li>"
                    else:
                        buf = "<li>"+ line +"</li>"
            if len(buf) < 1:
                continue
            #print((" "*indent_level)+buf)
            cache["output"].append(("  "*indent_level)+buf)
            indent_level += indent_change 
        print(cache["output"])

    def organize(self, cache):
        pages = "pages"
        tables = "tables"
        bold = "bold"
        quotes = "quotes"
        cache["outline"] = {
                pages:[],   # Pages
                1:[],       # Header 1 / Top Page
                2:[],       # Header 2 / Inner Page
                3:[],       # Header 3 
                4:[],       # Header 4 
                5:[],       # Header 5 
                6:[],       # Header 6
                tables:[],  # Tables
                bold:[],    # Bold
                quotes:[ [], ],   # Quotes
                }
        current_level = 0
        current_page = -1
        table_found = False
        current_table = -1
        current_quote = 0
        for line in cache["output"]:
            #Check for ignore conditions
            tag = line
            if "<b>" in line:
                cache["outline"][bold].append(line)
            if "<h" in line.lstrip()[:2]: 
                if "<h1" in line:
                    current_page += 1
                    cache["outline"][pages].append( [] ) # Make a new page
                current_level = int(line.lstrip()[2])
                cache["outline"][current_level].append(line)
            elif "<table" in line:
                table_found = True
                current_table += 1
                cache["outline"][tables].append( [] )
            elif "</table" in line:
                table_found = False
                cache["outline"][tables][current_table].append(line)
            elif "quote" in line: 
                if "quote-author" in line:
                    cache["outline"][quotes][current_quote].append(line)
                    current_quote += 1
                    cache["outline"][quotes].append( [] )
                else:
                    cache["outline"][quotes][current_quote].append(line)

            if table_found:
                cache["outline"][tables][current_table].append(line)

            if current_page > -1:
                cache["outline"][pages][current_page].append(line)
            else:
                print("Line outside of page!") # Really shouldn't happen.
                print(line)
    
    def strip_header_tags(self, line):
       return re.sub("<[/]?h.*?>","", line)

    def hyphenate(self, line):
        return re.sub(" +", "-", line.strip())

    def underscore(self, line):
        return re.sub(" +", "_", line.strip())
    
    def compile_lines(self, lines):
        out = ""
        for l in lines:
           out += l +"\n"
        return out

    def title_case(self, line):
        # Taken from Python Documents for String Methods title()
        return re.sub(r"[A-Za-z]+('[A-Za-z]+)?", 
                lambda mo: mo.group(0)[0].upper() +
                            mo.group(0)[1:].lower(),
                            line)

    def pagify(self, cache, template):
        template_cache = {"input":[], "dictionary":{}}
        with open(template, "r") as f:
            template_cache["data"] = f.read()        


        # Make individual pages
        for page in cache["outline"]["pages"]:            
            # First line should be H1/ Title of the section
            buf = self.strip_header_tags(page[0]).strip()
            title = self.title_case(buf)
            title_id = self.hyphenate(title) 
            title_path = self.underscore(title)
            
            template_cache["dictionary"]["$TITLE"] = title
            template_cache["dictionary"]["$HEADER"] = page[0].strip()
            template_cache["dictionary"]["$CONTENT"] = self.compile_lines(page[1:])
            output = re.sub("\$[A-Z]+", lambda mo: template_cache["dictionary"][mo.group(0)], template_cache["data"])
            with open(title_path.lower()+".html","w") as out:
                out.write(output)



if __name__ == "__main__":
    if len(sys.argv) > 2:
        Exploder(sys.argv[1], sys.argv[2])
    else:
        Exploder(sys.argv[1], None)
