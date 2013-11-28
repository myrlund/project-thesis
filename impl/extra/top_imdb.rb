#!/usr/bin/env ruby
#
# Outputs a CSV document of the top 250 movies of IMDB, with the fields num, year, title.
#

require 'nokogiri'
require 'open-uri'

doc = Nokogiri::HTML(open('http://www.imdb.com/chart/top', "Accept-Language" => "en"))

puts "position,year,title"
doc.css('table.chart tr .titleColumn').each do |title_column|
  num = title_column.content.split(/\s+/).first[0...-1]
  title = title_column.css('a').first.content
  year = title_column.css('.secondaryInfo').first.content.match(/(\d+)/).captures.first
  
  puts "#{num},#{year},\"#{title.gsub('"', '""')}\""
end
