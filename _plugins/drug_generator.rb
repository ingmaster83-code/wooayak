require 'json'

module Jekyll
  class DrugPageGenerator < Generator
    safe true
    priority :normal

    def generate(site)
      drugs       = load_json(site, '_rawdata/drugs.json')
      supplements = load_json(site, '_rawdata/supplements.json')

      if drugs.any?
        Jekyll.logger.info "DrugGenerator:", "#{drugs.size}개 약품 페이지 생성 중..."
        drugs.each do |drug|
          next if drug['slug'].to_s.strip.empty?
          site.pages << DrugPage.new(site, drug)
        end
      end

      if supplements.any?
        Jekyll.logger.info "DrugGenerator:", "#{supplements.size}개 건강기능식품 페이지 생성 중..."
        supplements.each do |sup|
          next if sup['slug'].to_s.strip.empty?
          site.pages << SupplementPage.new(site, sup)
        end
      end

      # 통합 검색 인덱스 생성
      site.pages << SearchIndexPage.new(site, drugs, supplements)

      Jekyll.logger.info "DrugGenerator:", "완료 (약품 #{drugs.size} + 건강기능식품 #{supplements.size})"
    end

    private

    def load_json(site, path)
      file = File.join(site.source, path)
      return [] unless File.exist?(file)
      JSON.parse(File.read(file, encoding: 'utf-8'))
    rescue => e
      Jekyll.logger.warn "DrugGenerator:", "#{path} 로드 실패: #{e.message}"
      []
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
      self.data.merge!(drug)
      self.data['layout']      = 'drug'
      self.data['title']       = "#{drug['itemName']} 효능 용법 부작용"
      self.data['description'] = build_drug_desc(drug)
    end

    private

    def build_drug_desc(drug)
      return drug['seoDescription'] if drug['seoDescription'].to_s.length > 10
      efcy = (drug['efcyQesitm'] || '').strip[0, 80]
      name = drug['itemName'] || ''
      comp = drug['entpName'] || ''
      desc = "#{name}(#{comp}) 효능, 용법, 주의사항, 부작용을 확인하세요."
      desc += " #{efcy}" if efcy.length > 0
      desc[0, 155]
    end
  end

  class SupplementPage < Page
    def initialize(site, sup)
      @site = site
      @base = site.source
      @dir  = "supplement/#{sup['slug']}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'supplement.html')
      self.data.merge!(sup)
      self.data['layout']      = 'supplement'
      self.data['title']       = "#{sup['itemName']} 기능성 효능 섭취법"
      self.data['description'] = build_sup_desc(sup)
    end

    private

    def build_sup_desc(sup)
      return sup['seoDescription'] if sup['seoDescription'].to_s.length > 10
      name   = sup['itemName'] || ''
      fnclty = (sup['primaryFnclty'] || '').strip[0, 80]
      desc   = "#{name} 건강기능식품의 기능성, 일일 섭취량, 주의사항을 확인하세요."
      desc  += " #{fnclty}" if fnclty.length > 0
      desc[0, 155]
    end
  end

  class SearchIndexPage < Page
    def initialize(site, drugs, supplements)
      @site = site
      @base = site.source
      @dir  = ''
      @name = 'search_index.json'

      self.process(@name)
      self.data = { 'layout' => nil, 'sitemap' => false }

      drug_index = drugs.map do |d|
        {
          'type'        => 'drug',
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

      sup_index = supplements.map do |s|
        {
          'type'        => 'supplement',
          'slug'        => s['slug'],
          'itemName'    => s['itemName'],
          'entpName'    => s['entpName'] || '',
          'efcyQesitm'  => (s['primaryFnclty'] || '')[0, 100],
          'itemImage'   => '',
          'rawMaterial' => (s['rawMaterial'] || '')[0, 60],
        }
      end

      self.content = (drug_index + sup_index).to_json
    end

    def output   = self.content
    def render(layouts, registers); end
  end
end
