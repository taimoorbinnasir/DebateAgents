export default function ReportContent({ text }) {
  const blocks = parseReport(text)

  return (
    <div className="space-y-4 text-left">
      {blocks.map((block, i) => {
        if (block.type === "heading") {
          return (
            <h3 key={i} className="text-sm font-bold text-purple-700 uppercase
                                    tracking-wide border-b border-purple-100 pb-1 pt-2">
              {block.content}
            </h3>
          )
        }

        if (block.type === "table") {
          return (
            <div key={i} className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-purple-50">
                    {block.headers.map((h, j) => (
                      <th key={j} className="text-left px-3 py-2 font-semibold text-gray-700 border-b border-gray-200">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, r) => (
                    <tr key={r} className={r % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                      {row.map((cell, c) => (
                        <td key={c} className="px-3 py-2 text-gray-600 border-b border-gray-100">
                          {formatInline(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }

        if (block.type === "list") {
          return (
            <ul key={i} className="space-y-1.5 pl-1">
              {block.items.map((item, j) => (
                <li key={j} className="text-sm text-gray-700 flex gap-2">
                  <span className="text-purple-400 mt-0.5">•</span>
                  <span>{formatInline(item)}</span>
                </li>
              ))}
            </ul>
          )
        }

        // paragraph
        return (
          <p key={i} className="text-sm text-gray-700 leading-relaxed">
            {formatInline(block.content)}
          </p>
        )
      })}
    </div>
  )
}

// Convert *emphasis* to CAPS, same rule as FormattedText
function formatInline(text) {
  return text.replace(/\*{1,2}([^*]+)\*{1,2}/g, (match, content) => content.toUpperCase())
}

function parseReport(text) {
  const lines = text.split("\n")
  const blocks = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i].trim()

    // Empty line — skip
    if (!line) { i++; continue }

    // Markdown heading: ## Heading or **Heading:**
    const headingMatch = line.match(/^#{1,3}\s*(.+)$/) || line.match(/^\*\*([^*]+):?\*\*$/)
    if (headingMatch) {
      blocks.push({ type: "heading", content: headingMatch[1].replace(/:$/, "") })
      i++
      continue
    }

    // Table: line starts with | and next line is a separator (---|---)
    if (line.startsWith("|")) {
      const headers = line.split("|").map(c => c.trim()).filter(Boolean)
      i++
      // Skip separator line (|---|---|)
      if (lines[i] && lines[i].includes("---")) i++

      const rows = []
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        const row = lines[i].split("|").map(c => c.trim()).filter(Boolean)
        if (row.length) rows.push(row)
        i++
      }

      blocks.push({ type: "table", headers, rows })
      continue
    }

    // Numbered/bulleted list — group consecutive list items
    if (/^(\d\)|\d\.|-|\*)\s/.test(line)) {
      const items = []
      while (i < lines.length && /^(\d\)|\d\.|-|\*)\s/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^(\d\)|\d\.|-|\*)\s/, ""))
        i++
      }
      blocks.push({ type: "list", items })
      continue
    }

    // Regular paragraph — collect until blank line
    let para = line
    i++
    while (i < lines.length && lines[i].trim() && !lines[i].trim().startsWith("|") && !/^(\d\)|\d\.|-|\*)\s/.test(lines[i].trim())) {
      para += " " + lines[i].trim()
      i++
    }
    blocks.push({ type: "paragraph", content: para })
  }

  return blocks
}