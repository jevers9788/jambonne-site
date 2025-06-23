import json
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
from typing import Dict, List
import re

def create_mind_map_visualization(mind_map_data: Dict, output_file: str = "mind_map.png"):
    """Create a visual mind map from the scraped data."""
    
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_xlim(-10, 10)
    ax.set_ylim(-8, 8)
    ax.axis('off')
    
    # Central topic
    central_x, central_y = 0, 0
    central_box = FancyBboxPatch(
        (central_x - 1.5, central_y - 0.5), 3, 1,
        boxstyle="round,pad=0.1",
        facecolor='lightblue',
        edgecolor='darkblue',
        linewidth=2
    )
    ax.add_patch(central_box)
    ax.text(central_x, central_y, mind_map_data['central_topic'], 
            ha='center', va='center', fontsize=14, fontweight='bold')
    
    branches = mind_map_data['branches']
    if not branches:
        ax.text(0, -2, "No content found", ha='center', va='center', fontsize=12)
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        return
    
    # Calculate positions for branches
    n_branches = len(branches)
    angles = np.linspace(0, 2*np.pi, n_branches, endpoint=False)
    radius = 4
    
    for i, (branch, angle) in enumerate(zip(branches, angles)):
        # Calculate branch position
        branch_x = central_x + radius * np.cos(angle)
        branch_y = central_y + radius * np.sin(angle)
        
        # Draw connection line
        ax.plot([central_x, branch_x], [central_y, branch_y], 
                'k-', alpha=0.5, linewidth=1)
        
        # Create branch box
        title = branch['topic']
        if len(title) > 30:
            title = title[:27] + "..."
        
        # Adjust box size based on content length
        content_length = branch['content_length']
        if content_length > 3000:
            box_width, box_height = 2.5, 1.2
            color = 'lightgreen'
        elif content_length > 1000:
            box_width, box_height = 2.2, 1.0
            color = 'lightyellow'
        else:
            box_width, box_height = 2.0, 0.8
            color = 'lightcoral'
        
        branch_box = FancyBboxPatch(
            (branch_x - box_width/2, branch_y - box_height/2), 
            box_width, box_height,
            boxstyle="round,pad=0.05",
            facecolor=color,
            edgecolor='darkgray',
            linewidth=1
        )
        ax.add_patch(branch_box)
        
        # Add title text
        ax.text(branch_x, branch_y, title, 
                ha='center', va='center', fontsize=10, fontweight='bold',
                wrap=True)
        
        # Add content length indicator
        ax.text(branch_x, branch_y - box_height/2 - 0.2, 
                f"{content_length} chars", 
                ha='center', va='top', fontsize=8, alpha=0.7)
    
    plt.title("Safari Reading List Mind Map", fontsize=16, fontweight='bold', pad=20)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Mind map visualization saved to {output_file}")

def create_text_summary(mind_map_data: Dict, output_file: str = "mind_map_summary.txt"):
    """Create a text summary of the mind map data."""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("SAFARI READING LIST MIND MAP SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Central Topic: {mind_map_data['central_topic']}\n")
        f.write(f"Total Articles: {len(mind_map_data['branches'])}\n\n")
        
        total_chars = sum(branch['content_length'] for branch in mind_map_data['branches'])
        f.write(f"Total Content: {total_chars:,} characters\n\n")
        
        f.write("BRANCHES:\n")
        f.write("-" * 20 + "\n\n")
        
        for i, branch in enumerate(mind_map_data['branches'], 1):
            f.write(f"{i}. {branch['topic']}\n")
            f.write(f"   URL: {branch['url']}\n")
            f.write(f"   Content Length: {branch['content_length']:,} characters\n")
            f.write(f"   Preview: {branch['content_preview']}\n")
            f.write("\n")
    
    print(f"Text summary saved to {output_file}")

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract common keywords from text for mind map enhancement."""
    # Simple keyword extraction (you could enhance this with NLP libraries)
    words = re.findall(r'\b\w{4,}\b', text.lower())
    
    # Remove common stop words
    stop_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 
                  'were', 'said', 'each', 'which', 'their', 'time', 'would', 
                  'there', 'could', 'other', 'than', 'first', 'very', 'after',
                  'some', 'what', 'when', 'where', 'more', 'most', 'over',
                  'into', 'through', 'during', 'before', 'after', 'above',
                  'below', 'between', 'among', 'within', 'without', 'against'}
    
    words = [word for word in words if word not in stop_words]
    
    # Count frequency
    word_count = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1
    
    # Return most common words
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_keywords]]

def create_enhanced_mind_map(mind_map_data: Dict, output_file: str = "enhanced_mind_map.png"):
    """Create an enhanced mind map with keyword analysis."""
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16))
    ax.set_xlim(-12, 12)
    ax.set_ylim(-10, 10)
    ax.axis('off')
    
    # Central topic
    central_x, central_y = 0, 0
    central_box = FancyBboxPatch(
        (central_x - 2, central_y - 0.6), 4, 1.2,
        boxstyle="round,pad=0.1",
        facecolor='lightblue',
        edgecolor='darkblue',
        linewidth=3
    )
    ax.add_patch(central_box)
    ax.text(central_x, central_y, mind_map_data['central_topic'], 
            ha='center', va='center', fontsize=16, fontweight='bold')
    
    branches = mind_map_data['branches']
    if not branches:
        return
    
    # Calculate positions for branches
    n_branches = len(branches)
    angles = np.linspace(0, 2*np.pi, n_branches, endpoint=False)
    radius = 5
    
    # Collect all content for keyword analysis
    all_content = " ".join([branch.get('scraped_content', '') for branch in branches])
    common_keywords = extract_keywords(all_content, 15)
    
    # Draw keyword cloud in background
    keyword_radius = 8
    keyword_angles = np.linspace(0, 2*np.pi, len(common_keywords), endpoint=False)
    for keyword, angle in zip(common_keywords, keyword_angles):
        kw_x = central_x + keyword_radius * np.cos(angle)
        kw_y = central_y + keyword_radius * np.sin(angle)
        ax.text(kw_x, kw_y, keyword, ha='center', va='center', 
                fontsize=8, alpha=0.3, color='gray')
    
    for i, (branch, angle) in enumerate(zip(branches, angles)):
        # Calculate branch position
        branch_x = central_x + radius * np.cos(angle)
        branch_y = central_y + radius * np.sin(angle)
        
        # Draw connection line
        ax.plot([central_x, branch_x], [central_y, branch_y], 
                'k-', alpha=0.6, linewidth=2)
        
        # Create branch box
        title = branch['topic']
        if len(title) > 25:
            title = title[:22] + "..."
        
        content_length = branch['content_length']
        if content_length > 3000:
            box_width, box_height = 3, 1.5
            color = 'lightgreen'
        elif content_length > 1000:
            box_width, box_height = 2.8, 1.3
            color = 'lightyellow'
        else:
            box_width, box_height = 2.5, 1.1
            color = 'lightcoral'
        
        branch_box = FancyBboxPatch(
            (branch_x - box_width/2, branch_y - box_height/2), 
            box_width, box_height,
            boxstyle="round,pad=0.05",
            facecolor=color,
            edgecolor='darkgray',
            linewidth=2
        )
        ax.add_patch(branch_box)
        
        # Add title text
        ax.text(branch_x, branch_y, title, 
                ha='center', va='center', fontsize=11, fontweight='bold',
                wrap=True)
        
        # Add content length indicator
        ax.text(branch_x, branch_y - box_height/2 - 0.3, 
                f"{content_length:,} chars", 
                ha='center', va='top', fontsize=9, alpha=0.8)
        
        # Extract keywords for this specific article
        article_keywords = extract_keywords(branch.get('scraped_content', ''), 5)
        if article_keywords:
            keyword_text = ", ".join(article_keywords[:3])
            ax.text(branch_x, branch_y + box_height/2 + 0.3, 
                    keyword_text, 
                    ha='center', va='bottom', fontsize=8, alpha=0.7,
                    style='italic')
    
    plt.title("Enhanced Safari Reading List Mind Map", fontsize=18, fontweight='bold', pad=30)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Enhanced mind map saved to {output_file}")

def main():
    """Main function to create mind map visualizations."""
    try:
        # Load mind map data
        with open("mind_map_data.json", 'r', encoding='utf-8') as f:
            mind_map_data = json.load(f)
        
        print("Creating mind map visualizations...")
        
        # Create basic mind map
        create_mind_map_visualization(mind_map_data, "mind_map.png")
        
        # Create enhanced mind map with keywords
        create_enhanced_mind_map(mind_map_data, "enhanced_mind_map.png")
        
        # Create text summary
        create_text_summary(mind_map_data, "mind_map_summary.txt")
        
        print("\nAll visualizations created successfully!")
        print("- mind_map.png: Basic mind map")
        print("- enhanced_mind_map.png: Enhanced mind map with keywords")
        print("- mind_map_summary.txt: Text summary")
        
    except FileNotFoundError:
        print("Error: mind_map_data.json not found. Please run reading_list.py first.")
    except Exception as e:
        print(f"Error creating visualizations: {e}")

if __name__ == "__main__":
    main() 