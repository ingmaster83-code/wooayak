require 'json'

module Jekyll
  class DrugPageGenerator < Generator
    safe true
    priority :normal

    def generate(site)
      drugs_file = File.join(site.source, '_data', 'drugs.json')
      return unless File.exist?(drugs_file)

      drugs = JSON.parse(File.read(drugs_file, encoding: 'utf-8'))
      Jekyll.logger.info "DrugGenerator:", "#{drugs.size}개 약품 페이지 생성 중..."

      drugs.each do |drug|
        next if drug['slug'].to_s.strip.empty?

        site.pages << DrugPage.new(site, drug)
      end

      # 검색 인덱스 생성
      site.pages << SearchIndexPage.new(site, drugs)

      Jekyll.logger.info "DrugGenerator:", "완료"
    end
  end

  class DrugPage < Page
    def initialize(site, drug)
      @site = site
      @base = site.source
      @dir  = "drug/#{drug['slug']}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'drug.html')

      # front matter에 약품 데이터 주입
      self.data.merge!(drug)
      self.data['layout']      = 'drug'
      self.data['title']       = "#{drug['itemName']} 효능 용법 부작용"
      self.data['description'] = build_description(drug)
    end

    private

    def build_description(drug)
      # seoDescription이 있으면 우선 사용
      return drug['seoDescription'] if drug['seoDescription'].to_s.length > 10

      efcy = (drug['efcyQesitm'] || '').strip[0, 80]
      name = drug['itemName'] || ''
      comp = drug['entpName'] || ''
      desc = "#{name}(#{comp}) 효능, 용법, 주의사항, 부작용을 확인하세요."
      desc += " #{efcy}" if efcy.length > 0
      desc[0, 155]
    end
  end

  class SearchIndexPage < Page
    def initialize(site, drugs)
      @site = site
      @base = site.source
      @dir  = ''
      @name = 'search_index.json'

      self.process(@name)
      self.data = {
        'layout'    => nil,
        'sitemap'   => false,
      }

      # 검색에 필요한 필드만 추출 (파일 크기 최소화)
      index = drugs.map do |d|
        {
          'slug'        => d['slug'],
          'itemName'    => d['itemName'],
          'entpName'    => d['entpName'],
          'efcyQesitm'  => (d['efcyQesitm'] || '')[0, 100],
          'itemImage'   => d['itemImage'],
          'drugShape'   => d['drugShape'],
          'colorClass1' => d['colorClass1'],
          'colorClass2' => d['colorClass2'],
          'formCodeName'=> d['formCodeName'],
          'printFront'  => d['printFront'],
          'printBack'   => d['printBack'],
          'lineFront'   => d['lineFront'],
          'lineBack'    => d['lineBack'],
        }
      end

      self.content = index.to_json
    end

    def output
      self.content
    end

    def render(layouts, registers)
      # 레이아웃 없이 JSON 그대로 출력
    end
  end
end
